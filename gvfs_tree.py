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

from ctypes import *
from binascii import hexlify
import os
import mmap
import socket
import types

# some aliases
guchar = c_ubyte
guint32 = c_uint32
guint64 = c_uint64

# some data
META_MAGIC = bytearray(b"\xda\x1ameta")
MAJOR_VERSION = 1
MINOR_VERSION = 0

# https://github.com/GNOME/gvfs/blob/master/metadata/metatree.c
class MetaFileHeader(BigEndianStructure):
  _fields_ = [
    ("magic", guchar * 6),        # binary magic
    ("major", guchar),            # binary major version
    ("minor", guchar),            # binary minor version
    ("rotated", guint32),         # ?
    ("random_tag", guint32),      # ?
    ("root", guint32),            # root directory information
    ("attributes", guint32),      # offset (*attributes is attributes_length, attributes[n] is n-th attribute name (string))
    ("time_t_base", guint64)      # absolute time to use as base. Other times are relative to this.
  ]

  def __str__(self):
    return "MetaFileHeader[magic=%s] Ver %u.%u - %u (root=%u, attributes=%u) (rotated=%u, random_tag=%u)" % (
      hexlify(self.magic), self.major, self.minor, self.time_t_base,
      self.root, self.attributes, self.rotated, self.random_tag)

  def valid(self):
    return(self.magic == META_MAGIC) and (self.major == MAJOR_VERSION) and (self.minor == MINOR_VERSION)

class MetaFileDirEnt(BigEndianStructure):
  _fields_ = [
    ("name", guint32),            # *name is node name
    ("children", guint32),        # offset (*children is children length, children[n] is n-th MetaFileDirEnt child)
    ("metadata", guint32),        # TODO, key->value metadata
    ("last_changed", guint32)     # last_change relative time
  ]

  def __str__(self):
    return "MetaFileDirEnt[name=%u][children=%u][metadata=%u][last_changed=%u]" % (
      self.name, self.children, self.metadata, self.last_changed
    )

class MetaTree:
  def __init__(self, f, size):
    self.file = f
    self.size = size
    self.data = mmap.mmap(f.fileno(), size, mmap.MAP_PRIVATE, mmap.PROT_READ)
    self.header = MetaFileHeader.from_buffer_copy(self.data)
    assert(self.header.valid())
    self.root = self.read_ctype(self.header.root, MetaFileDirEnt)
    self.attributes = self.read_attributes_array()

  def read_ctype(self, pos, ctype_cls):
    assert(pos + sizeof(ctype_cls) < self.size)
    return ctype_cls.from_buffer_copy(self.data, pos)

  def read_string(self, string_pos):
    assert(string_pos < self.size)
    end_pos = self.data.find(b'\0', string_pos)
    assert(end_pos != None)
    s = self.data[string_pos:end_pos]
    return s

  def read_array(self, pos, item_getter, item_size):
    num_elems = socket.ntohl(self.read_ctype(pos, guint32).value)
    elems = []

    assert(pos + sizeof(guint32) + (num_elems * item_size) < size)

    for i in range(num_elems):
      offset = pos + sizeof(guint32) + (i * item_size)
      elem = item_getter(offset)
      elems.append(elem)

    return elems

  def read_attributes_array(self):
    return self.read_array(self.header.attributes, lambda pos: self.read_string(socket.ntohl(self.read_ctype(pos, guint32).value)), sizeof(guint32))

  def read_ctype_array(self, offset, ctype_cls):
    return self.read_array(offset, lambda pos: self.read_ctype(pos, ctype_cls), sizeof(ctype_cls))

  def recursive_print(self, dir_ent_node=None, level=0):
    if not dir_ent_node:
      dir_ent_node = self.root

    print("%s%s" % ("  " * level, metatree.read_string(dir_ent_node.name).decode("utf-8")))
    children = self.read_ctype_array(dir_ent_node.children, MetaFileDirEnt)

    if children:
      for child in children:
        self.recursive_print(dir_ent_node=child, level=level+1)

if __name__ == "__main__":
  import sys

  fpath = sys.argv[1]
  size = os.stat(fpath).st_size

  with open(fpath, "rb") as f:
    metatree = MetaTree(f, size)
    metatree.recursive_print()
