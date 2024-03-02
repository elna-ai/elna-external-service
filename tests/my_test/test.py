from ic.agent import Agent
from ic.candid import Types, decode, encode
from ic.client import Client
from ic.identity import Identity

# Identity and Client are dependencies of Agent
iden = Identity()
client = Client(url="http://127.0.0.1:4943")
agent = Agent(iden, client)

name = agent.query_raw("bkyz2-fmaaa-aaaaa-qaaaq-cai", "get", encode([]))
print(name)
# transfer 100 token to blackhole address `aaaaa-aa`
# params = [
# 	{'type': Types.Principal, 'value': 'aaaaa-aa'},
# 	{'type': Types.Nat, 'value': 10000000000}
# ]
result = agent.update_raw("bkyz2-fmaaa-aaaaa-qaaaq-cai", "inc", encode([]))
name = agent.query_raw("bkyz2-fmaaa-aaaaa-qaaaq-cai", "get", encode([]))
print(name)
