from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent
from ic.candid import encode, decode, Types
from ic.principal import Principal

# Identity and Client are dependencies of Agent
identity = Identity()
client = Client(url="https://ic0.app")
agent = Agent(identity, client)


def main():
    # test_principal = Principal.from_str('4cay5-ew3bs-vr6yl-7iffu-67doc-l655v-dluy7-qplpx-7pkio-er5rt-uqe')

    encoded_args = encode(
        [
            {
                "type": Types.Principal,
                "value": "4cay5-ew3bs-vr6yl-7iffu-67doc-l655v-dluy7-qplpx-7pkio-er5rt-uqe",
            }
        ]
    )

    response = agent.query_raw(
        "6qy4q-5aaaa-aaaah-adwma-cai", "getUserToken", encoded_args
    )
    print(response)


if __name__ == "__main__":
    main()
