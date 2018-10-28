This repository contains utilities to exctract
[GVfs](https://wiki.gnome.org/Projects/gvfs/doc#Metadata) metadata information.

GVfs usually stores metadata in the user directory `~/.local/share/gvfs-metadata/`. The tree
structure of any location mounted by the user (e.g. any external peripheral mounted via
a nautilus-based file manager) is permanently stored into such directory as well as its
related metadata. This provides usuful information for forensics.

The tool `gvfs_tree.py` prints the directory structure of one of the gvfs locations.
Here is an example:

  `python gvfs_tree.py ~/.local/share/gvfs-metadata/uuid-2017-02-15-20-36-22-00`

It will print out the `uuid-2017-02-15-20-36-22-00` device directory structure, even if it's
currently not connected:

```
/
  pool
    main
      m
        maas
```

Some special locations are the `root` and `home` locations, which contain the root file system and
user home directory structure and metadata. Some example of file metadata are the icons locations.

# Fuse

Dependecies:

- fusepy (install with `pip install fusepy`)

Run:

```
  python gvfs_meta_mount.py ~/mnt
```

# Links

- https://wiki.gnome.org/Projects/gvfs/doc#Metadata
- https://en.wikipedia.org/wiki/GVfs
- https://github.com/GNOME/gvfs/blob/master/metadata/metatree.c
- http://cyberforensicator.com/wp-content/uploads/2018/04/GVFS-metadata-Shellbags-for-Linux.pdf
