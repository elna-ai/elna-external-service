"""Analytics Handler - Simplified Counter Only
"""
from typing import Dict, Any

class AnalyticsDataHandler:
    """Handle the request data for the service - counter only."""

    id_attribute = 'bot-id'
    counter_attribute = 'msg_count'

    def __init__(self, table_name, client, logger):
        self._table_name = table_name
        self._logger = logger
        self.table = client.Table(self._table_name)

    def put_data(self, bot_id):
        """put data into dynamoDB - Simple counter increment

        Args:
            bot_id (str): bot id
        """
        response = self.table.get_item(Key={self.id_attribute: bot_id})

        if 'Item' in response:
            # Item exists, increment the counter
            existing_item = response['Item']
            new_count = existing_item[self.counter_attribute] + 1

            # Update the item with the new count
            self.table.update_item(
                Key={self.id_attribute: bot_id},
                UpdateExpression=f"SET {self.counter_attribute} = :new_count",
                ExpressionAttributeValues={":new_count": new_count}
            )

            self._logger.info(msg=f"Item with ID {bot_id} exists. Count incremented to {new_count}")
        else:
            # Item does not exist, create a new row
            self.table.put_item(Item={self.id_attribute: bot_id, self.counter_attribute: 1})
            self._logger.info(msg=f"New item with ID {bot_id} created with count 1")

    def get_agent_count(self, agent_id: str) -> int:
        """Get the message count for a specific agent
        
        Args:
            agent_id (str): Agent identifier
            
        Returns:
            int: Message count for the agent
        """
        try:
            response = self.table.get_item(Key={self.id_attribute: agent_id})
            if 'Item' in response:
                return response['Item'].get(self.counter_attribute, 0)
            return 0
        except Exception as e:
            self._logger.error(f"Failed to get agent count: {str(e)}")
            return 0

    def get_all_agent_counts(self) -> Dict[str, int]:
        """Get message counts for all agents
        
        Returns:
            Dict mapping agent_id to message count
        """
        try:
            response = self.table.scan()
            agent_counts = {}
            
            for item in response.get('Items', []):
                agent_id = item.get(self.id_attribute)
                count = item.get(self.counter_attribute, 0)
                if agent_id:
                    agent_counts[agent_id] = count
            
            return agent_counts
        except Exception as e:
            self._logger.error(f"Failed to get all agent counts: {str(e)}")
            return {}