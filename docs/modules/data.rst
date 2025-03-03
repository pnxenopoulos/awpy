Data
===========

Awpy packages data artifacts (map images, parsed navigation meshes, map triangles, etc.) separately from the code.
These artifacts are liable to change with game updates. We try to maintain as much history as we can, but we can't guarantee that we have all the data for all game versions.
Data is stored on `awpycs.com` as `awpycs.com/{patch}/{artifact}.{filetype}`. Most things like map images, parsed navigation meshes and map triangles are stored as `.zip` files.
The triangles are the largest (roughly 20MB), but most are a few MB compressed.
To see what artifacts are available and what the current patch is, you can run

.. code-block:: bash

    awpy artifacts

To get a specific artifact, you can run something like the following, which will grab all the triangles for the current patch.

.. code-block:: bash

    awpy get tris

If you want to specify a patch, you can do so with the `--patch` flag.

.. code-block:: bash

    awpy get tris --patch 123456789

The data is stored in the Awpy directory, which is `$HOME/.awpy`