This repository contains utilities to exctract
[GVfs](https://wiki.gnome.org/Projects/gvfs/doc#Metadata) metadata information.

The GVfs framework is used by nautilus based file managers (e.g. caja) to handle virtual and phisical devices. Metadata include, for example, attributes like icon position for desktop icons, emblem icon, download uri for pdf file. When a user selects a drive and mounts it from the file manager gui, the device metadata is saved into a GVfs metadata folder. This folder is located at `~/.local/share/gvfs-metadata` and every device has a subdirectory under this folder. Any subsequent interaction with the device via the file manager adds more metadata to the device folder.

One problem with this is that the retention time of such metadata is not clear. It seems like old data is never removed even after some user actions like "Clear Recent Documents". This means that such metadata is a usefull information source for forensicts, as described in the [GVFS metadata: Shellbags for Linux paper](http://cyberforensicator.com/wp-content/uploads/2018/04/GVFS-metadata-Shellbags-for-Linux.pdf).

The tools in this repo can extract GVfs metadata information to perform forensicts analysis. Metadata includes:
  - Virtual/physical device name
  - Directory tree structure and file names
  - File last changed timestamp
  - File attributes used by the file manager

Some special locations under `~/.local/share/gvfs-metadata` are the home and root locations, which contain the root file system and user home directory metadata.
  
# Cli tool

The tool `gvfs_tree.py` prints the directory tree structure of one of the gvfs metadata locations.
Here is an example:

  `python gvfs_tree.py ~/.local/share/gvfs-metadata/uuid-2017-02-15-20-36-22-00`

It will print out the `uuid-2017-02-15-20-36-22-00` device directory structure, even if it's currently not connected:

```
/
  pool
    main
      m
        maas
```

# FUSE module

The FUSE module provides an easy way to inspect metadata and folder structure. It is structured in the following way:
  - The main directory contains all the valid GVfs metadata files (corresponding to virtual devices/locations)
  - Each metadata file can be explored as a directory
  - Individual files have all the timestamps (creation time, access time, ...) set to the last changed timestamp extracted from the metadata
  - The contents of each file contains the metadata attributes of the file

The module is not optimized and is in early development.

Dependecies:

- fusepy (install with `pip install fusepy`)

Run:

```
  python gvfs_meta_mount.py ~/mnt --root ~/.local/share/gvfs-metadata
```

The directory `~/mnt` can now be explored via command line or a file manager. The script stays in foreground. Use `-v` to print debugging information.

# Links

- https://wiki.gnome.org/Projects/gvfs/doc#Metadata
- https://en.wikipedia.org/wiki/GVfs
- https://github.com/GNOME/gvfs/blob/master/metadata/metatree.c
- http://cyberforensicator.com/wp-content/uploads/2018/04/GVFS-metadata-Shellbags-for-Linux.pdf
