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

import os
from metadata import MetaTree
import argparse

def recursive_print(dir_ent_node, level=0):
  print("%s%s" % ("  " * level, dir_ent_node.get_name()))
  children = dir_ent_node.get_children()

  if children:
    for child in children:
      recursive_print(child, level+1)

parser = argparse.ArgumentParser(description='Print GVfs metadata directory tree.')
parser.add_argument('fpath', type=argparse.FileType('r'), help='the input GVfs metadata file')
args = parser.parse_args()

fpath = args.fpath.name
size = os.stat(fpath).st_size

with open(fpath, "rb") as f:
  metatree = MetaTree(f, size)
  recursive_print(metatree.root)
