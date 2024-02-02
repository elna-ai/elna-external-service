"""Analytics Handler
"""
class AnalyticsDataHandler:
    """Handle the request data for the service."""

    id_attribute = 'bot-id'
    counter_attribute = 'msg_count'


    def __init__(self, table_name, client, logger):
        self._table_name = table_name
        self._logger = logger
        self.table = client.Table(self._table_name)

    def put_data(self,bot_id):
        """put data into dynamoDB

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
