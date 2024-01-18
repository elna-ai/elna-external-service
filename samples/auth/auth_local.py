from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent
from ic.candid import encode, decode, Types


# Identity and Client are dependencies of Agent
iden = Identity()
client = Client(url="http://localhost:4943")
agent = Agent(iden, client)


def main():
    encoded_args = encode(
        [
            {
                "type": Types.Principal,
                "value": "4cay5-ew3bs-vr6yl-7iffu-67doc-l655v-dluy7-qplpx-7pkio-er5rt-uqe",
            }
        ]
    )

    resp = agent.query_raw("bkyz2-fmaaa-aaaaa-qaaaq-cai", "getUserToken", encoded_args)
    print(resp)


if __name__ == "__main__":
    main()
