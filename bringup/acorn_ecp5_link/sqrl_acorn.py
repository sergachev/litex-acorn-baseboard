#!/usr/bin/env python3

#
# This file is part of LiteICLink.
#
# Copyright (c) 2017-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import sys
import argparse

from migen import *

from litex_boards.platforms import sqrl_acorn

from litex.build.generic_platform import *

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.code_8b10b import K

from liteiclink.serdes.gtp_7series import GTPQuadPLL, GTP

# IOs ----------------------------------------------------------------------------------------------

_transceiver_io = [
    # SFP
    ("sfp_tx", 0,
        Subsignal("p", Pins("D7")),
        Subsignal("n", Pins("C7"))
    ),
    ("sfp_rx", 0,
        Subsignal("p", Pins("D9")),
        Subsignal("n", Pins("C9"))
    ),

    # PCIe
    ("pcie_tx", 0,
        Subsignal("p", Pins("D11")),
        Subsignal("n", Pins("C11"))
    ),
    ("pcie_rx", 0,
        Subsignal("p", Pins("D5")),
        Subsignal("n", Pins("C5"))
    ),

    # ECP5
    ("ecp5_tx", 0,
     Subsignal("p", Pins("B4")),
     Subsignal("n", Pins("A4"))
     ),
    ("ecp5_rx", 0,
     Subsignal("p", Pins("B8")),
     Subsignal("n", Pins("A8"))
     ),
]

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys       = ClockDomain()

        # Clk/Rst
        clk200 = platform.request("clk200")

        # PLL
        self.submodules.pll = pll = S7PLL()
        self.comb += pll.reset.eq(self.rst)
        pll.register_clkin(clk200, 200e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

# GTPTestSoC ---------------------------------------------------------------------------------------

class GTPTestSoC(SoCMini):
    def __init__(self, platform, connector, linerate):
        assert connector in ["sfp", "pcie", "ecp5"]
        sys_clk_freq = int(100e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, sys_clk_freq,
            ident         = "LiteICLink bench on Acorn CLE 215+",
            ident_version = True,
            with_uart     = True,
            uart_name     = "uartbone"
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform, sys_clk_freq)

        # GTP RefClk -------------------------------------------------------------------------------
        self.clock_domains.cd_refclk = ClockDomain()
        refclk_freq = 200e6
        self.crg.pll.create_clkout(self.cd_refclk, refclk_freq)
        platform.add_platform_command("set_property SEVERITY {{Warning}} [get_drc_checks REQP-49]")

        # GTP PLL ----------------------------------------------------------------------------------
        pll = GTPQuadPLL(self.cd_refclk.clk, refclk_freq, linerate)
        print(pll)
        self.submodules += pll

        # GTP --------------------------------------------------------------------------------------
        tx_pads = platform.request(connector + "_tx")
        rx_pads = platform.request(connector + "_rx")
        self.submodules.serdes0 = serdes0 = GTP(pll, tx_pads, rx_pads, sys_clk_freq,
            tx_buffer_enable = True,
            rx_buffer_enable = True,
            tx_polarity      = 1,
            rx_polarity      = 1,
            clock_aligner    = False)
        serdes0.add_stream_endpoints()
        serdes0.add_controls()
        serdes0.add_clock_cycles()
        self.add_csr("serdes0")

        platform.add_period_constraint(serdes0.cd_tx.clk, 1e9/serdes0.tx_clk_freq)
        platform.add_period_constraint(serdes0.cd_rx.clk, 1e9/serdes0.rx_clk_freq)
        self.platform.add_false_path_constraints(self.crg.cd_sys.clk, serdes0.cd_tx.clk, serdes0.cd_rx.clk)

        # Test -------------------------------------------------------------------------------------
        counter = Signal(32)
        self.sync.tx += counter.eq(counter + 1)

        # K28.5 and slow counter --> TX
        self.comb += [
            serdes0.sink.valid.eq(1),
            serdes0.sink.ctrl.eq(0b1),
            serdes0.sink.data[:8].eq(K(28, 5)),
            serdes0.sink.data[8:].eq(counter[26:]),
        ]

        # RX (slow counter) --> Leds
        self.comb += serdes0.source.ready.eq(1)
        self.comb += platform.request("user_led", 3).eq(serdes0.source.data[8])

        # Leds -------------------------------------------------------------------------------------
        sys_counter = Signal(32)
        self.sync.sys += sys_counter.eq(sys_counter + 1)
        self.comb += platform.request("user_led", 0).eq(sys_counter[26])

        tx_counter = Signal(32)
        self.sync.tx += tx_counter.eq(tx_counter + 1)
        self.comb += platform.request("user_led", 1).eq(tx_counter[26])

        rx_counter = Signal(32)
        self.sync.rx += rx_counter.eq(rx_counter + 1)
        self.comb += platform.request("user_led", 2).eq(rx_counter[26])

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteICLink transceiver example on Acorn CLE 215+")
    parser.add_argument("--build",     action="store_true", help="Build bitstream")
    parser.add_argument("--load",      action="store_true", help="Load bitstream (to SRAM)")
    parser.add_argument("--connector", default="ecp5",      help="Connector")
    parser.add_argument("--linerate",  default="800e6",     help="Line rate")
    args = parser.parse_args()

    platform = sqrl_acorn.Platform()
    platform.add_extension(_transceiver_io)
    soc = GTPTestSoC(platform,
        connector = args.connector,
        linerate  = float(args.linerate),
    )
    builder = Builder(soc, csr_csv="sqrl_acorn.csv")
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
