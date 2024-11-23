#!/usr/bin/env python3
#
# gvfs-meta-explorer
# (C) 2018 Emanuele Faranda
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import errno
import math
import os
import stat

import fuse

from metadata import MetaTree

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)


class GvfsMetadataFS(fuse.Fuse):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.root_path = None
        self.metatrees = {}
        self.uid = os.getuid()
        self.gid = os.getgid()

    def fsinit(self, root):
        self.root_path = os.path.expanduser(root)

    @staticmethod
    def metatree_open(path):
        size = os.stat(path).st_size
        f = open(path, "rb")
        return MetaTree(f, size)

    def list_available_files(self):
        if not self.metatrees:
            for f in os.listdir(self.root_path):
                try:
                    metatree = self.metatree_open(os.path.join(self.root_path, f))
                    metatree.file.close()
                    self.metatrees[f] = None
                except (AssertionError, ValueError):
                    pass
        return list(self.metatrees.keys())

    @staticmethod
    def stat(path):
        st = os.stat(path)
        return fuse.Stat(**{key: getattr(st, key) for key in ('st_atime', 'st_ctime', 'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid', 'st_blocks')})

    def list_meta_files(self, path_parts, parent_tree=None):
        metafile = path_parts[0]

        if not parent_tree:
            if not metafile in self.metatrees:
                return []

            if not self.metatrees[metafile]:
                # first level
                self.metatrees[metafile] = self.metatree_open(os.path.join(self.root_path, metafile))

            metatree = self.metatrees[metafile].root
        elif not metafile in parent_tree:
            return []
        else:
            metatree = parent_tree[metafile]

        children = metatree.get_children()

        if len(path_parts) == 1:
            return [meta.get_name() for meta in children]
        else:
            key_based = {child.get_name(): child for child in children}
            return self.list_meta_files(path_parts[1:], key_based)

    def find_node_recursive(self, path_parts, parent_tree=None):
        metafile = path_parts[0]
        node = None

        if not parent_tree:
            # first level
            if not metafile in self.metatrees:
                return

            tree = self.metatrees[metafile]
            if not tree:
                return

            node = tree.root
        else:
            # Inner level
            for child in parent_tree.get_children():
                if child.get_name() == metafile:
                    node = child
                    break

        if not node:
            return

        if len(path_parts) == 1:
            return node
        else:
            return self.find_node_recursive(path_parts[1:], parent_tree=node)

    @staticmethod
    def metadata_as_contents(metadata):
        return "\n".join(f"{key}={value}" for key, value in sorted(metadata.items()))

    def getattr(self, path: str):
        if path == "/":
            return self.stat(self.root_path)

        parts = path.lstrip("/").split("/")
        if len(parts) == 1:
            # First level
            files = self.list_available_files()
            if parts[0] in files:
                st = self.stat(os.path.join(self.root_path, parts[0]))
                st.st_mode = stat.S_IFDIR | 0o555 | (st.st_mode & 0o777)
                return st
        elif len(parts) > 0 and parts[0] in self.metatrees:
            # Inner level
            node = self.find_node_recursive(parts)

            if node:
                last_changed = node.get_last_changed()
                file_content = self.metadata_as_contents(node.get_metadata())

                s = fuse.Stat(**{
                    "st_atime": last_changed, "st_ctime": last_changed, "st_mtime": last_changed,
                    "st_uid": self.uid, "st_gid": self.gid, "st_nlink": 1,
                    "st_size": len(file_content), "st_blocks": math.ceil(len(file_content) / 512),
                })

                is_dir = len(node.get_children()) > 0
                if is_dir:
                    s.st_mode = stat.S_IFDIR | 0o755
                else:
                    s.st_mode = stat.S_IFREG | 0o644
                return s

        return -errno.ENOENT

    def readdir(self, path, *_):
        parts = path.lstrip("/").split("/")
        paths = []

        if len(parts) > 0:
            if parts[0] == "":
                # First level: just list dirs
                paths = self.list_available_files()
            else:
                # Inner level
                paths = self.list_meta_files(parts)

        yield fuse.Direntry(".")
        yield fuse.Direntry("..")
        yield from map(fuse.Direntry, paths)

    def read(self, path, length, offset):
        parts = path.lstrip("/").split("/")
        node = self.find_node_recursive(parts)

        if node:
            file_contents = self.metadata_as_contents(node.get_metadata())
            return file_contents[offset:offset + length].encode("utf-8")


if __name__ == '__main__':
    fs = GvfsMetadataFS()
    fs.parse(errex=1)
    if fs.fuse_args.mountpoint is None:
        fs.fuse_args.modifiers["showhelp"] = True
    if fs.fuse_args.mount_expected():
        src, = fs.cmdline[1]
        fs.fsinit(src)

    fs.main()
