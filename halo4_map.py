# halo4_map.py — parser + patcher for Halo 4 MCC (.map) cache files.
#
# Halo 4 is the next cache generation after Reach, and on MCC it stays close enough
# to reach_map.ReachMap that this is a thin subclass of a thin subclass. Verified
# empirically against all 10 shipped campaign maps (m05_prologue .. m95_epilogue).
# LITTLE-endian, header version 13, 'daeh' magic — all shared with Halo 3 and Reach.
#
# The FOUR divergences from Reach, and nothing else:
#
#   1. THE HEADER TAIL IS SHIFTED 8 BYTES EARLIER. Halo 3 and Reach put the virtual
#      base at 0x2E0, the index-header VA at 0x2E8, the six-entry partition table at
#      0x300 and the checksum at 0x360. Halo 4 puts them at 0x2D8 / 0x2E0 / 0x2F8 /
#      0x358. Everything from 0x00..0x100 (magic, version, build, internal name,
#      scenario name, the four string-table descriptors) is unmoved.
#
#   2. PARTITION SIZE IS 32-BIT. Reach's entry is [load u64][size u64]; Halo 4 keeps
#      the 0x10 stride but stores [load u64][size u32][u32]. That trailing word is
#      NOT padding — partition 0 carries a non-zero value there (a hash, most
#      likely) — so reading the size as a u64 the way Reach does yields nonsense.
#      The six partitions are still contiguous and still in file order.
#
#   3. HEADER SIZE 0x1E000, checksum at 0x358. `foot` sits at 0x1DFFC on every
#      campaign map, and the XOR from 0x1E000 to EOF reproduces the shipped
#      checksum byte-exactly on all ten. This is the same trap Reach's 0xA000 was:
#      update_checksum XORs from HEADER_SIZE, so an inherited figure writes a wrong
#      checksum into every patched map and nothing complains until the game does.
#
#   4. THE TAG-DATA REGION SITS 0x10000 EARLIER IN FILE THAN THE INDEX HEADER
#      ANCHOR SAYS. Halo 3 and Reach both pin the six partitions to the file by the
#      one address whose file offset is known outright -- the index header's, found
#      by its magic -- and in those games tag-data space and index space agree at
#      that point. Halo 4 offsets them by a flat 0x10000: measured identically on
#      all ten campaign maps against the object-type word every object tag carries
#      at +0x0 (bipd 0, vehi 1, weap 2, eqip 3, proj 5, scen 6, mach 7, ctrl 8 --
#      note ssce is 10 here where Reach has 9, and the upper 16 bits are flags).
#      Without the correction every tag base lands 0x10000 into the wrong data and
#      every reflexive reads a count of -1 or 0, which looks exactly like "this map
#      does not have that field" rather than like a broken parser.
#
#   5. THE NAME-BLOB SENTINEL IS A DIFFERENT LINE OF THE SAME SONG. Reach anchors
#      its string-table bias recovery on "i've got a lovely bunch of coconuts";
#      Halo 4's joke tag name is "there they are all standing in a row". The
#      recovery method is otherwise identical and works identically — all four
#      tables ship intact, displaced by one shared constant K.
#
# Everything else — the '343i'-guarded index header at +0x48, the 0x5000_0000
# tag-data address bias, group entries, tag entries, reflexives, tagRefs,
# apply_field, save() — is inherited from ReachMap unchanged.
#
# Value edits only; no structural growth (same as Reach).

import struct

from reach_map import ReachMap


class Halo4Map(ReachMap):
    """Parsed Halo 4 MCC cache. See the module docstring for the four ways it
    differs from ReachMap; every other behaviour is inherited unchanged."""

    HEADER_SIZE = 0x1E000       # 'foot' at 0x1DFFC; Reach 0xA000, Halo 3 0x4000
    CHECKSUM_OFF = 0x358        # Reach and Halo 3 both use 0x360

    # The header tail moved 8 bytes earlier than Reach's. Named rather than inlined
    # so the three users below read as "the same field, a different address".
    VIRT_BASE_OFF = 0x2D8
    INDEX_VA_OFF = 0x2E0
    PARTITION_OFF = 0x2F8
    BUILD_OFF = 0x98            # Reach and Halo 3: 0xA0
    INTERNAL_NAME_OFF = 0xB8    # Reach and Halo 3: 0xC0
    SCENARIO_NAME_OFF = 0xD8    # Reach and Halo 3: 0xE0
    # How far the tag-data space runs AHEAD of index space at the index header.
    # Zero in Halo 3 and Reach; a flat 0x10000 on every Halo 4 campaign map.
    INDEX_GAP = 0x10000

    _NAME_BLOB_SENTINEL = b"there they are all standing in a row\x00"

    def _parse_header(self):
        """Identical to Halo 3 / Reach except for the five moved fields.

        The shift starts somewhere after the four string-table descriptors at
        0x20..0x3C -- those read correctly at Halo 3's offsets, and file_tbl_count
        matching n_tags exactly on every campaign map is the proof -- and covers
        everything from the build stamp onward. The scenario name matters most: it
        is one of the two anchors `_recover_table_bias` verifies against, so reading
        it eight bytes late silently costs the map every tag name AND every
        stringID, with `names_stripped` as the only complaint.
        """
        super()._parse_header()
        self.build = self._cstr(self.BUILD_OFF)
        self.internal_name = self._cstr(self.INTERNAL_NAME_OFF)
        self.scenario_name = self._cstr(self.SCENARIO_NAME_OFF)
        self.virt_base = self.u64(self.VIRT_BASE_OFF)
        self.index_header_va = self.u64(self.INDEX_VA_OFF)

    def _parse_partitions(self):
        """Reach's partition walk with Halo 4's table address and 32-bit sizes.

        The body is Halo3Map's, not re-derived: only the two reads at the top --
        table base and size width -- change, and the anchoring off the partition
        holding the index header is what makes the file bases fall out.
        """
        self.partitions = []
        for i in range(6):
            e = self.PARTITION_OFF + i * 0x10
            self.partitions.append([self.u64(e), self.u32(e + 8), None])
        self._locate_index_header()
        self.idx_delta = self.index_header_va - self.index_header_off
        ap = self._part_of(self.index_header_va)
        if ap is not None:
            fbase_ap = self.index_header_off - (self.index_header_va
                                               - self.partitions[ap][0])
            pre = sum(self.partitions[j][1] for j in range(ap))
            cur = fbase_ap - pre
            cur -= self.INDEX_GAP
            for i in range(6):
                self.partitions[i][2] = cur
                cur += self.partitions[i][1]
