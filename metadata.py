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

import mmap
import socket
from ctypes import c_ubyte, c_uint32, c_uint64, BigEndianStructure, sizeof

# some aliases
guchar = c_ubyte
guint32 = c_uint32
guint64 = c_uint64

# some data
META_MAGIC = bytearray(b"\xda\x1ameta")
MAJOR_VERSION = 1
MINOR_VERSION = 0
KEY_IS_LIST_MASK = 1 << 31

META_KEY_TYPE_NONE = 0
META_KEY_TYPE_STRING = 1
META_KEY_TYPE_STRINGV = 2


# https://github.com/GNOME/gvfs/blob/master/metadata/metatree.c
class _MetaFileHeader(BigEndianStructure):
    _fields_ = [
        ("magic", guchar * 6),  # binary magic
        ("major", guchar),  # binary major version
        ("minor", guchar),  # binary minor version
        ("rotated", guint32),  # flag to avoid a race condition
        ("random_tag", guint32),  # tag used for the journal
        ("root", guint32),  # root directory information
        ("attributes", guint32),  # offset (*attributes is attributes_length, attributes[n] is n-th attribute name (string))
        ("time_t_base", guint64)  # absolute time to use as base. Other times are relative to this.
    ]

    def __str__(self):
        return f"_MetaFileHeader[magic={self.magic!r}] Ver {self.major}.{self.minor} - {self.time_t_base} (root={self.root}, attributes={self.attributes}) (rotated={self.rotated}, random_tag={self.random_tag})"

    def valid(self):
        return (self.magic == META_MAGIC) and (self.major == MAJOR_VERSION) and (self.minor == MINOR_VERSION)


class _MetaFileDirEnt(BigEndianStructure):
    _fields_ = [
        ("name", guint32),  # *name is node name
        ("children", guint32),  # offset (*children is children length, children[n] is n-th MetaFileDirEnt child)
        ("metadata", guint32),  # key->value metadata
        ("last_changed", guint32)  # last_change relative time
    ]

    def __str__(self):
        return f"MetaFileDirEnt[name={self.name}][children={self.children}][metadata={self.metadata}][last_changed={self.last_changed}]"


class _MetaFileDataEnt(BigEndianStructure):
    _fields_ = [
        ("key", guint32),
        ("value", guint32),
    ]

    def __str__(self):
        return f"MetaFileDataEnt[key={self.key}][value={self.value}]"


class MetaFileDirEnt:
    def __init__(self, metatree, node, parent_node):
        self.metatree = metatree
        self.node = node
        self.parent = parent_node

    def get_name(self):
        return self.metatree.read_string(self.node.name).decode("utf-8")

    def get_children(self):
        return [MetaFileDirEnt(self.metatree, node, self) for node in self.metatree.read_ctype_array(self.node.children, _MetaFileDirEnt)]

    def get_metadata(self):
        if self.node.metadata == 0:
            return {}

        metadatas = self.metatree.read_ctype_array(self.node.metadata, _MetaFileDataEnt)
        kv = {}

        for meta in metadatas:
            key_id = (meta.key & ~KEY_IS_LIST_MASK) & 0xFFFFFFFF
            if meta.key & KEY_IS_LIST_MASK:
                val_type = META_KEY_TYPE_STRINGV
            else:
                val_type = META_KEY_TYPE_STRING

            if key_id >= len(self.metatree.attributes):
                continue

            key_name = self.metatree.attributes[key_id]
            if not key_name:
                continue

            if val_type == META_KEY_TYPE_STRING:
                value = self.metatree.read_string(meta.value)
            else:
                # TODO implement stringv type read
                raise NotImplementedError

            if value:
                kv[key_name.decode("utf-8")] = value.decode("utf-8")

        return kv

    def get_last_changed(self):
        return self.node.last_changed + self.metatree.header.time_t_base


class MetaTree:
    def __init__(self, f, size):
        self.file = f
        self.size = size
        # it's writable just for convenience (we can use from_buffer instead of from_buffer_copy)
        self.data = mmap.mmap(f.fileno(), size, mmap.MAP_PRIVATE)
        self.header = _MetaFileHeader.from_buffer(self.data)
        assert self.header.valid()
        self.root = MetaFileDirEnt(self, self.read_ctype(self.header.root, _MetaFileDirEnt), None)
        self.attributes = self.read_attributes_array()

    def read_ctype(self, pos, ctype_cls):
        assert pos + sizeof(ctype_cls) < self.size
        return ctype_cls.from_buffer(self.data, pos)

    def read_string(self, string_pos):
        assert (string_pos < self.size)
        end_pos = self.data.find(b'\0', string_pos)
        assert end_pos is not None
        s = self.data[string_pos:end_pos]
        return s

    def read_array(self, pos, item_getter, item_size):
        if pos == 0:
            return []

        num_elems = socket.ntohl(self.read_ctype(pos, guint32).value)
        elems = []

        assert pos + sizeof(guint32) + (num_elems * item_size) < self.size

        for i in range(num_elems):
            offset = pos + sizeof(guint32) + (i * item_size)
            elem = item_getter(offset)
            elems.append(elem)

        return elems

    def read_attributes_array(self):
        return self.read_array(self.header.attributes, lambda pos: self.read_string(socket.ntohl(self.read_ctype(pos, guint32).value)), sizeof(guint32))

    def read_ctype_array(self, offset, ctype_cls):
        return self.read_array(offset, lambda pos: self.read_ctype(pos, ctype_cls), sizeof(ctype_cls))
