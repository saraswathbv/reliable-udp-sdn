
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3


class SimpleSwitch(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch, self).__init__(*args, **kwargs)

        self.datapaths = {}
        self.primary_up = True

        self.logger.info("Reliable UDP SDN Controller started")

    def add_flow(self, dp, priority, match, actions):

        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        flow = parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=instructions
        )

        dp.send_msg(flow)

    def install_paths(self):

        if not all(i in self.datapaths for i in (1, 2, 3)):
            self.logger.info(
                "Waiting for switches. Connected: %s",
                list(self.datapaths.keys())
            )
            return

        s1 = self.datapaths[1]
        s2 = self.datapaths[2]
        s3 = self.datapaths[3]

        # Delete previous forwarding rules
        for dp in (s1, s2, s3):

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

        # Install default drop rules
        for dp in (s1, s2, s3):

            parser = dp.ofproto_parser

            dp.send_msg(
                parser.OFPFlowMod(
                    datapath=dp,
                    priority=0,
                    match=parser.OFPMatch(),
                    instructions=[]
                )
            )

        if self.primary_up:

            self.logger.info(
                "ACTIVE PATH: PRIMARY H1-S1-S2-S3-H2"
            )

            rules = [
                (s1, 1, 2),
                (s2, 1, 2),
                (s3, 2, 1),
                (s3, 1, 2),
                (s2, 2, 1),
                (s1, 2, 1)
            ]

        else:

            self.logger.warning(
                "ACTIVE PATH: BACKUP H1-S1-S3-H2"
            )

            rules = [
                (s1, 1, 3),
                (s3, 3, 1),
                (s3, 1, 3),
                (s1, 3, 1)
            ]

        for dp, in_port, out_port in rules:

            parser = dp.ofproto_parser

            match = parser.OFPMatch(
                in_port=in_port
            )

            actions = [
                parser.OFPActionOutput(out_port)
            ]

            self.add_flow(
                dp,
                100,
                match,
                actions
            )

        self.logger.info("Forwarding rules sent to all switches")

    @set_ev_cls(
        ofp_event.EventOFPSwitchFeatures,
        CONFIG_DISPATCHER
    )
    def switch_features(self, ev):

        dp = ev.msg.datapath

        self.datapaths[dp.id] = dp

        self.logger.info(
            "Switch %s connected",
            dp.id
        )

        self.install_paths()

    @set_ev_cls(
        ofp_event.EventOFPPortStatus,
        MAIN_DISPATCHER
    )
    def port_status(self, ev):

        msg = ev.msg
        dp = msg.datapath

        # Only S1 port 2 monitors the primary link
        if dp.id != 1 or msg.desc.port_no != 2:
            return

        down = bool(
            msg.desc.state & dp.ofproto.OFPPS_LINK_DOWN
        )

        new_state = not down

        if new_state == self.primary_up:
            return

        self.primary_up = new_state

        if self.primary_up:

            self.logger.info(
                "PRIMARY LINK RESTORED - switching to primary"
            )

        else:

            self.logger.warning(
                "PRIMARY LINK FAILED - switching to backup"
            )

        self.install_paths()

    @set_ev_cls(
        ofp_event.EventOFPPacketIn,
        MAIN_DISPATCHER
    )
    def packet_in(self, ev):

        # Configured paths handle forwarding.
        # Do not flood packets in the cyclic topology.
        return

