from mininet.topo import Topo


class ReliableUDPTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Connect hosts to switches
        self.addLink(h1, s1)
        self.addLink(h2, s3)

        # Primary path
        self.addLink(s1, s2)
        self.addLink(s2, s3)

        # Alternative path
        self.addLink(s1, s3)


topos = {
    'reliableudp': lambda: ReliableUDPTopo()
}
