import gettext
_ = gettext.gettext
import os

PROGNAME = "system-config-lvm"
INSTALLDIR="/usr/share/system-config-lvm/"



LVM_PATH="/usr/sbin/"
LVMDISKSCAN_BIN_PATH = LVM_PATH + 'lvmdiskscan'
if os.access(LVMDISKSCAN_BIN_PATH, os.F_OK) == False:
    LVM_PATH="/sbin/"
LVM_BIN_PATH = LVM_PATH + 'lvm'
LVMDISKSCAN_BIN_PATH = LVM_PATH + 'lvmdiskscan'
LVDISPLAY_BIN_PATH = LVM_PATH + 'lvdisplay'
LVCREATE_BIN_PATH = LVM_PATH + 'lvcreate'
LVCHANGE_BIN_PATH = LVM_PATH + 'lvchange'
LVCONVERT_BIN_PATH = LVM_PATH + 'lvconvert'
LVRENAME_BIN_PATH = LVM_PATH + 'lvrename'
LVEXTEND_BIN_PATH = LVM_PATH + 'lvextend'
LVREDUCE_BIN_PATH = LVM_PATH + 'lvreduce'
LVREMOVE_BIN_PATH = LVM_PATH + 'lvremove'
PVCREATE_BIN_PATH = LVM_PATH + 'pvcreate'
PVREMOVE_BIN_PATH = LVM_PATH + 'pvremove'
PVMOVE_BIN_PATH = LVM_PATH + 'pvmove'
VGCREATE_BIN_PATH = LVM_PATH + 'vgcreate'
VGCHANGE_BIN_PATH = LVM_PATH + 'vgchange'
VGEXTEND_BIN_PATH = LVM_PATH + 'vgextend'
VGREDUCE_BIN_PATH = LVM_PATH + 'vgreduce'
VGREMOVE_BIN_PATH = LVM_PATH + 'vgremove'
SCSIID_BIN_PATH = "/sbin/scsi_id"

###Types of views to render
UNSELECTABLE_TYPE = 0
VG_TYPE = 1
VG_PHYS_TYPE = 2
VG_LOG_TYPE = 3
PHYS_TYPE = 4
LOG_TYPE = 5
UNALLOCATED_TYPE = 6
UNINITIALIZED_TYPE = 7

NAME_COL = 0
TYPE_COL = 1
PATH_COL = 2
SIMPLE_LV_NAME_COL = 3
OBJ_COL = 4

#INIT_ENTITY=_("Are you certain that you wish to initialize disk entity %s? All data will be lost on this device/partition.")
INIT_ENTITY=_("All data on disk entity %s will be lost! Are you certain that you wish to initialize it?")
INIT_ENTITY_FILESYSTEM=_("Disk entity %s contains %s filesystem. All data on it will be lost! Are you certain that you wish to initialize disk entity %s?")
INIT_ENTITY_MOUNTED=_("Disk entity %s contains data from directory %s. All data in it will be lost! Are you certain that you wish to initialize disk entity %s?")
INIT_ENTITY_FREE_SPACE=_("Are you certain that you wish to initialize %s of free space on disk %s?")
INIT_ENTITY_DEVICE_CHOICE=_("You are about to initialize unpartitioned disk %s. It is advisable, although not required, to create a partition on it. Do you want to create a single partition encompassing the whole drive?")

RELOAD_LVM_MESSAGE=_("Reloading LVM. Please wait.")

RESTART_COMPUTER=_("Changes will take effect after computer is restarted. If device %s is used, before restart, data corruption WILL occur. It is advisable to restart your computer now.")

MIRROR_LOG=_("Mirror Log")

UNABLE_TO_PROCESS_REQUEST=_("Unable to process request")

COMMAND_FAILURE=_("%s command failed. Command attempted: \"%s\" - System Error Message: %s")

NEW_LV_NAME_ARG = 0
NEW_LV_VGNAME_ARG = 1
NEW_LV_SIZE_ARG = 2
NEW_LV_UNIT_ARG = 3
NEW_LV_IS_STRIPED_ARG = 4
NEW_LV_STRIPE_SIZE_ARG = 5
NEW_LV_NUM_STRIPES_ARG = 6
NEW_LV_SNAPSHOT = 7
NEW_LV_SNAPSHOT_ORIGIN = 8
NEW_LV_MIRRORING = 9

EXTENT_IDX = 0
GIGABYTE_IDX = 1
MEGABYTE_IDX = 2
KILOBYTE_IDX = 3

UNUSED=_("Unused")
FREE=_("Free")
FREE_SPACE=_("Free space")

UNPARTITIONED_SPACE=_("Unpartitioned space")
UNPARTITIONED_SPACE_ON=_("Unpartitioned space on %s")

GIG_SUFFIX=_("GB")
MEG_SUFFIX=_("MB")
KILO_SUFFIX=_("KB")
BYTE_SUFFIX=_("Bytes")


#File System Types
NO_FILESYSTEM=_("No Filesystem")
EXT2_T=_("Ext2")
EXT3_T=_("Ext3")
JFS_T=_("JFS")
MSDOS_T=_("MSDOS")
REISERFS_T=_("Reiserfs")
VFAT_T=_("VFAT")
XFS_T=_("XFS")
CRAMFS_T=_("Cramfs")



# UI support for mirroring
MIRRORING_UI_SUPPORT = True
