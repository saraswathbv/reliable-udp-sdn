from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet


class SimpleSwitch(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Switch ports in the existing Mininet topology:
    # S1: port 1 = H1, port 2 = S2, port 3 = S3
    # S2: port 1 = S1, port 2 = S3
    # S3: port 1 = H2, port 2 = S2, port 3 = S1

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.primary_up = True

    def add_flow(self, dp, priority, match, actions):
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS, actions
            )
        ]

        dp.send_msg(
            parser.OFPFlowMod(
                datapath=dp,
                priority=priority,
                match=match,
                instructions=instructions
            )
        )

    def install_paths(self):
        """Install fixed forwarding rules without flooding."""
        if not all(dpid in self.datapaths for dpid in (1, 2, 3)):
            self.logger.info("Waiting for all three switches")
            return

        # Remove old forwarding rules.
        for dp in self.datapaths.values():
            parser = dp.ofproto_parser
            dp.send_msg(
                parser.OFPFlowMod(
                    datapath=dp,
                    command=dp.ofproto.OFPFC_DELETE,
                    out_port=dp.ofproto.OFPP_ANY,
                    out_group=dp.ofproto.OFPG_ANY,
                    match=parser.OFPMatch()
                )
            )

        # Install a table-miss rule that drops unmatched packets.
        for dp in self.datapaths.values():
            parser = dp.ofproto_parser
            ofproto = dp.ofproto
            dp.send_msg(
                parser.OFPFlowMod(
                    datapath=dp,
                    priority=0,
                    match=parser.OFPMatch(),
                    instructions=[]
                )
            )

        s1 = self.datapaths[1]
        s2 = self.datapaths[2]
        s3 = self.datapaths[3]

        if self.primary_up:
            # Primary path: H1 -> S1 -> S2 -> S3 -> H2
            rules = [
                (s1, 1, 2),
                (s2, 1, 2),
                (s3, 2, 1),
                # Reverse path: H2 -> S3 -> S2 -> S1 -> H1
                (s3, 1, 2),
                (s2, 2, 1),
                (s1, 2, 1),
            ]
            self.logger.info("Installing PRIMARY path through S2")
        else:
            # Backup path: H1 -> S1 -> S3 -> H2
            rules = [
                (s1, 1, 3),
                (s3, 3, 1),
                # Reverse path: H2 -> S3 -> S1 -> H1
                (s3, 1, 3),
                (s1, 3, 1),
            ]
            self.logger.info("Installing BACKUP path through S3")

        for dp, in_port, out_port in rules:
            parser = dp.ofproto_parser
            match = parser.OFPMatch(in_port=in_port)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(dp, 100, match, actions)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.logger.info("Switch %s connected", dp.id)
        self.install_paths()

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status(self, ev):
        msg = ev.msg
        dp = msg.datapath

        # S1 port 2 connects to S2 port 1.
        if dp.id == 1 and msg.desc.port_no == 2:
            down = bool(
                msg.desc.state & dp.ofproto.OFPPS_LINK_DOWN
            )
            self.primary_up = not down
            self.logger.info(
                "Primary link S1-S2 status changed: %s",
                "DOWN" if down else "UP"
            )
            self.install_paths()

        # S2 port 1 is the other end of the same link.
        elif dp.id == 2 and msg.desc.port_no == 1:
            down = bool(
                msg.desc.state & dp.ofproto.OFPPS_LINK_DOWN
            )
            self.primary_up = not down
            self.logger.info(
                "Primary link S1-S2 status changed: %s",
                "DOWN" if down else "UP"
            )
            self.install_paths()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        # The configured paths handle forwarding.
        # Do not flood packets around the cyclic topology.
        return
