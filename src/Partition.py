

ID_UNKNOWN    = 10000 # hope nobody will use this one on real partition table 
ID_EMPTY      = -1
ID_EXTENDS    = [0x5, 0xf, 0x85]
ID_SWAPS      = [0x82]
ID_LINUX_LVM  = 0x8e
ID_GPT        = 238

PARTITION_IDs = { -1 : 'NONE',
                  0 : 'Empty',
                  1 : 'FAT12',
                  2 : 'XENIX root',
                  3 : 'XENIX usr',
                  4 : 'FAT16 <32M',
                  5 : 'Extended',
                  6 : 'FAT16',
                  7 : 'HPFS/NTFS',
                  8 : 'AIX',
                  9 : 'AIX bootable',
                  10 : 'OS/2 Boot Manager',
                  11 : 'W95 FAT32',
                  12 : 'W95 FAT32 (LBA)',
                  14 : 'W95 FAT16 (LBA)',
                  15 : 'W95 Ext\'d (LBA)',
                  16 : 'OPUS',
                  17 : 'Hidden FAT12',
                  18 : 'Compaq diagnostics',
                  20 : 'Hidden FAT16 <32M',
                  22 : 'Hidden FAT16',
                  23 : 'Hidden HPFS/NTFS',
                  24 : 'AST SmartSleep',
                  27 : 'Hidden W95 FAT32',
                  28 : 'Hidden W95 FAT32 (LBA)',
                  30 : 'Hidden W95 FAT16 (LBA)',
                  36 : 'NEC DOS',
                  57 : 'Plan 9',
                  60 : 'PartitionMagic recovery',
                  64 : 'Venix 80286',
                  65 : 'PPC PReP Boot',
                  66 : 'SFS',
                  77 : 'QNX4.x',
                  78 : 'QNX4.x 2nd part',
                  79 : 'QNX4.x 3rd part',
                  80 : 'OnTrack DM',
                  81 : 'OnTrack DM6 Aux1',
                  82 : 'CP/M',
                  83 : 'OnTrack DM6 Aux3',
                  84 : 'OnTrackDM6',
                  85 : 'EZ-Drive',
                  86 : 'Golden Bow',
                  92 : 'Priam Edisk',
                  97 : 'SpeedStor',
                  99 : 'GNU HURD or SysV',
                  100 : 'Novell Netware 286',
                  101 : 'Novell Netware 386',
                  112 : 'DiskSecure Multi-Boot',
                  117 : 'PC/IX',
                  128 : 'Old Minix',
                  129 : 'Minix / old Linux',
                  130 : 'Linux swap',
                  131 : 'Linux',
                  132 : 'OS/2 hidden C: drive',
                  133 : 'Linux extended',
                  134 : 'NTFS volume set',
                  135 : 'NTFS volume set',
                  142 : 'Linux LVM',
                  147 : 'Amoeba',
                  148 : 'Amoeba BBT',
                  159 : 'BSD/OS',
                  160 : 'IBM Thinkpad hibernation',
                  165 : 'FreeBSD',
                  166 : 'OpenBSD',
                  167 : 'NeXTSTEP',
                  168 : 'Darwin UFS',
                  169 : 'NetBSD',
                  171 : 'Darwin boot',
                  183 : 'BSDI fs',
                  184 : 'BSDI swap',
                  187 : 'Boot Wizard hidden',
                  190 : 'Solaris boot',
                  193 : 'DRDOS/sec (FAT-12)',
                  196 : 'DRDOS/sec (FAT-16 < 32M)',
                  198 : 'DRDOS/sec (FAT-16)',
                  199 : 'Syrinx',
                  218 : 'Non-FS data',
                  219 : 'CP/M / CTOS / ...',
                  222 : 'Dell Utility',
                  223 : 'BootIt',
                  225 : 'DOS access',
                  227 : 'DOS R/O',
                  228 : 'SpeedStor',
                  235 : 'BeOS fs',
                  238 : 'EFI GPT',
                  239 : 'EFI (FAT-12/16/32)',
                  240 : 'Linux/PA-RISC boot',
                  241 : 'SpeedStor',
                  244 : 'SpeedStor',
                  242 : 'DOS secondary',
                  253 : 'Linux raid autodetect',
                  254 : 'LANstep',
                  255 : 'BBT',
                  ID_UNKNOWN : _("Unknown")}

# fill out gaps in PARTITION_IDs
for i in range(256):
    if i not in PARTITION_IDs:
        PARTITION_IDs[i] = _("Unknown")


# all size values are in sectors

class BlockDeviceSegment:
    def __init__(self, beg, end, sectorSize):
        self.children = list()
        self.beg = beg
        self.end = end
        self.sectorSize = sectorSize # bytes
        self.id = ID_EMPTY
        self.wholeDevice = False # occupies whole drive?
    def getSize(self):
        return self.end + 1 - self.beg
    def getSizeBytes(self):
        return self.getSize() * self.sectorSize
    def printout(self):
        print(' ', ' ', str(self.beg), str(self.end), str(self.id), str(self.getSize()), str(self.getSizeBytes()))

class Partition(BlockDeviceSegment):
    def __init__(self, beg, end, id, num, bootable, sectorSize):
        BlockDeviceSegment.__init__(self, beg, end, sectorSize)
        self.id = id
        self.num = num
        self.bootable = bootable
    def printout(self):
        self.__printout(self)
    def __printout(self, seg):
        if seg.bootable:
            b = 'b'
        else:
            b = ' '
        print(str(seg.num), b, str(seg.beg), str(seg.end), str(seg.id), str(seg.getSize()), str(self.getSizeBytes()))
        for child in seg.children:
            child.printout()
        
