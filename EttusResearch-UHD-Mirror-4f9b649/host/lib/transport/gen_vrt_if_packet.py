#!/usr/bin/env python
#
# Copyright 2010-2011 Ettus Research LLC
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

"""
The vrt packer/unpacker code generator:

This script will generate the pack and unpack routines that convert
metatdata into vrt headers and vrt headers into metadata.

The generated code infers jump tables to speed-up the parsing time.
"""

TMPL_TEXT = """
#import time
/***********************************************************************
 * This file was generated by $file on $time.strftime("%c")
 **********************************************************************/

\#include <uhd/exception.hpp>
\#include <uhd/transport/vrt_if_packet.hpp>
\#include <uhd/utils/byteswap.hpp>
\#include <boost/detail/endian.hpp>
\#include <vector>

//define the endian macros to convert integers
\#ifdef BOOST_BIG_ENDIAN
    \#define BE_MACRO(x) (x)
    \#define LE_MACRO(x) uhd::byteswap(x)
\#else
    \#define BE_MACRO(x) uhd::byteswap(x)
    \#define LE_MACRO(x) (x)
\#endif

using namespace uhd;
using namespace uhd::transport;

typedef size_t pred_type;
typedef std::vector<pred_type> pred_table_type;
#define pred_table_index(hdr) ((hdr >> 20) & 0x1ff)

static pred_table_type get_pred_unpack_table(void){
    pred_table_type table(1 << 9, 0); //only 9 bits useful here (20-28)
    for (size_t i = 0; i < table.size(); i++){
        boost::uint32_t vrt_hdr_word = i << 20;
        if(vrt_hdr_word & $hex(0x1 << 28)) table[i] |= $hex($sid_p);
        if(vrt_hdr_word & $hex(0x1 << 27)) table[i] |= $hex($cid_p);
        if(vrt_hdr_word & $hex(0x3 << 22)) table[i] |= $hex($tsi_p);
        if(vrt_hdr_word & $hex(0x3 << 20)) table[i] |= $hex($tsf_p);
        if(vrt_hdr_word & $hex(0x1 << 26)) table[i] |= $hex($tlr_p);
        if(vrt_hdr_word & $hex(0x1 << 24)) table[i] |= $hex($eob_p);
        if(vrt_hdr_word & $hex(0x1 << 25)) table[i] |= $hex($sob_p);
    }
    return table;
}

static const pred_table_type pred_unpack_table(get_pred_unpack_table());

//maps trailer bits to num empty bytes
//maps num empty bytes to trailer bits
static const size_t occ_table[] = {0, 2, 1, 3};

########################################################################
#def gen_code($XE_MACRO, $suffix)
########################################################################

void vrt::if_hdr_pack_$(suffix)(
    boost::uint32_t *packet_buff,
    if_packet_info_t &if_packet_info
){
    boost::uint32_t vrt_hdr_flags = 0;

    pred_type pred = 0;
    if (if_packet_info.has_sid) pred |= $hex($sid_p);
    if (if_packet_info.has_cid) pred |= $hex($cid_p);
    if (if_packet_info.has_tsi) pred |= $hex($tsi_p);
    if (if_packet_info.has_tsf) pred |= $hex($tsf_p);
    if (if_packet_info.has_tlr) pred |= $hex($tlr_p);
    if (if_packet_info.eob)     pred |= $hex($eob_p);
    if (if_packet_info.sob)     pred |= $hex($sob_p);

    switch(pred){
    #for $pred in range(2**7)
    case $pred:
        #set $num_header_words = 1
        #set $flags = 0
        ########## Stream ID ##########
        #if $pred & $sid_p
            packet_buff[$num_header_words] = $(XE_MACRO)(if_packet_info.sid);
            #set $num_header_words += 1
            #set $flags |= (0x1 << 28);
        #end if
        ########## Class ID ##########
        #if $pred & $cid_p
            packet_buff[$num_header_words] = 0; //not implemented
            #set $num_header_words += 1
            packet_buff[$num_header_words] = 0; //not implemented
            #set $num_header_words += 1
            #set $flags |= (0x1 << 27);
        #end if
        ########## Integer Time ##########
        #if $pred & $tsi_p
            packet_buff[$num_header_words] = $(XE_MACRO)(if_packet_info.tsi);
            #set $num_header_words += 1
            #set $flags |= (0x3 << 22);
        #end if
        ########## Fractional Time ##########
        #if $pred & $tsf_p
            packet_buff[$num_header_words] = $(XE_MACRO)(boost::uint32_t(if_packet_info.tsf >> 32));
            #set $num_header_words += 1
            packet_buff[$num_header_words] = $(XE_MACRO)(boost::uint32_t(if_packet_info.tsf >> 0));
            #set $num_header_words += 1
            #set $flags |= (0x1 << 20);
        #end if
        ########## Burst Flags ##########
        #if $pred & $eob_p
            #set $flags |= (0x1 << 24);
        #end if
        #if $pred & $sob_p
            #set $flags |= (0x1 << 25);
        #end if
        ########## Trailer ##########
        #if $pred & $tlr_p
            {
                const size_t empty_bytes = if_packet_info.num_payload_words32*sizeof(boost::uint32_t) - if_packet_info.num_payload_bytes;
                if_packet_info.tlr = (0x3 << 22) | (occ_table[empty_bytes & 0x3] << 10);
            }
            packet_buff[$num_header_words+if_packet_info.num_payload_words32] = $(XE_MACRO)(if_packet_info.tlr);
            #set $flags |= (0x1 << 26);
            #set $num_trailer_words = 1;
        #else
            #set $num_trailer_words = 0;
        #end if
        ########## Variables ##########
            if_packet_info.num_header_words32 = $num_header_words;
            if_packet_info.num_packet_words32 = $($num_header_words + $num_trailer_words) + if_packet_info.num_payload_words32;
            vrt_hdr_flags = $hex($flags);
        break;
    #end for
    }

    //fill in complete header word
    packet_buff[0] = $(XE_MACRO)(boost::uint32_t(0
        | (if_packet_info.packet_type << 29)
        | vrt_hdr_flags
        | ((if_packet_info.packet_count & 0xf) << 16)
        | (if_packet_info.num_packet_words32 & 0xffff)
    ));
}

void vrt::if_hdr_unpack_$(suffix)(
    const boost::uint32_t *packet_buff,
    if_packet_info_t &if_packet_info
){
    //extract vrt header
    boost::uint32_t vrt_hdr_word = $(XE_MACRO)(packet_buff[0]);
    size_t packet_words32 = vrt_hdr_word & 0xffff;

    //failure case
    if (if_packet_info.num_packet_words32 < packet_words32)
        throw uhd::value_error("bad vrt header or packet fragment");

    //extract fields from the header
    if_packet_info.packet_type = if_packet_info_t::packet_type_t(vrt_hdr_word >> 29);
    if_packet_info.packet_count = (vrt_hdr_word >> 16) & 0xf;

    const pred_type pred = pred_unpack_table[pred_table_index(vrt_hdr_word)];

    size_t empty_bytes = 0;

    switch(pred){
    #for $pred in range(2**7)
    case $pred:
        #set $has_time_spec = False
        #set $num_header_words = 1
        ########## Stream ID ##########
        #if $pred & $sid_p
            if_packet_info.has_sid = true;
            if_packet_info.sid = $(XE_MACRO)(packet_buff[$num_header_words]);
            #set $num_header_words += 1
        #else
            if_packet_info.has_sid = false;
        #end if
        ########## Class ID ##########
        #if $pred & $cid_p
            if_packet_info.has_cid = true;
            if_packet_info.cid = 0; //not implemented
            #set $num_header_words += 2
        #else
            if_packet_info.has_cid = false;
        #end if
        ########## Integer Time ##########
        #if $pred & $tsi_p
            if_packet_info.has_tsi = true;
            if_packet_info.tsi = $(XE_MACRO)(packet_buff[$num_header_words]);
            #set $num_header_words += 1
        #else
            if_packet_info.has_tsi = false;
        #end if
        ########## Fractional Time ##########
        #if $pred & $tsf_p
            if_packet_info.has_tsf = true;
            if_packet_info.tsf = boost::uint64_t($(XE_MACRO)(packet_buff[$num_header_words])) << 32;
            #set $num_header_words += 1
            if_packet_info.tsf |= $(XE_MACRO)(packet_buff[$num_header_words]);
            #set $num_header_words += 1
        #else
            if_packet_info.has_tsf = false;
        #end if
        ########## Burst Flags ##########
        #if $pred & $eob_p
            if_packet_info.eob = true;
        #else
            if_packet_info.eob = false;
        #end if
        #if $pred & $sob_p
            if_packet_info.sob = true;
        #else
            if_packet_info.sob = false;
        #end if
        ########## Trailer ##########
        #if $pred & $tlr_p
            if_packet_info.has_tlr = true;
            if_packet_info.tlr = $(XE_MACRO)(packet_buff[packet_words32-1]);
            #set $num_trailer_words = 1;
            {
                const int indicators = (if_packet_info.tlr >> 20) & (if_packet_info.tlr >> 8);
                if ((indicators & (1 << 0)) != 0) if_packet_info.eob = true;
                if ((indicators & (1 << 1)) != 0) if_packet_info.sob = true;
                empty_bytes = occ_table[(indicators >> 2) & 0x3];
            }
        #else
            if_packet_info.has_tlr = false;
            #set $num_trailer_words = 0;
        #end if
        ########## Variables ##########
            //another failure case
            if (packet_words32 < $($num_header_words + $num_trailer_words))
                throw uhd::value_error("bad vrt header or invalid packet length");
            if_packet_info.num_header_words32 = $num_header_words;
            if_packet_info.num_payload_words32 = packet_words32 - $($num_header_words + $num_trailer_words);
            if_packet_info.num_payload_bytes = if_packet_info.num_payload_words32*sizeof(boost::uint32_t) - empty_bytes;
        break;
    #end for
    }
}

########################################################################
#end def
########################################################################

$gen_code("BE_MACRO", "be")
$gen_code("LE_MACRO", "le")
"""

def parse_tmpl(_tmpl_text, **kwargs):
    from Cheetah.Template import Template
    return str(Template(_tmpl_text, kwargs))

if __name__ == '__main__':
    import sys
    open(sys.argv[1], 'w').write(parse_tmpl(
        TMPL_TEXT,
        file=__file__,
        sid_p = 0b0000001,
        cid_p = 0b0000010,
        tsi_p = 0b0000100,
        tsf_p = 0b0001000,
        tlr_p = 0b0010000,
        sob_p = 0b0100000,
        eob_p = 0b1000000,
    ))
