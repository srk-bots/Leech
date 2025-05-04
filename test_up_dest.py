from bot.helper.ext_utils.bot_utils import parse_chat_ids

class Listener:
    def __init__(self):
        self.up_dest = "123456789"
        
class TelegramUploader:
    def __init__(self, listener):
        self._listener = listener
        
    def test_up_dest(self):
        # Test if up_dest is a string
        print(f"Original up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Parse up_dest as a list of chat IDs
        if self._listener.up_dest:
            up_dest_id = self._listener.up_dest
            if isinstance(up_dest_id, list) and up_dest_id:
                up_dest_id = up_dest_id[0]  # Take the first item if it's a list
            
            print(f"Processed up_dest_id: {up_dest_id}, type: {type(up_dest_id)}")
            
            # Test if we can use it in a condition
            if up_dest_id != 12345:
                print("up_dest_id != 12345")
                
        # Now test with a list
        self._listener.up_dest = [123456789, 987654321]
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Parse up_dest as a list of chat IDs
        if self._listener.up_dest:
            up_dest_id = self._listener.up_dest
            if isinstance(up_dest_id, list) and up_dest_id:
                up_dest_id = up_dest_id[0]  # Take the first item if it's a list
            
            print(f"Processed up_dest_id: {up_dest_id}, type: {type(up_dest_id)}")
            
            # Test if we can use it in a condition
            if up_dest_id != 12345:
                print("up_dest_id != 12345")
                
        # Now test with a comma-separated string
        self._listener.up_dest = "123456789,987654321"
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Parse up_dest as a list of chat IDs
        if self._listener.up_dest:
            # Parse the string into a list
            from bot.helper.ext_utils.bot_utils import parse_chat_ids
            parsed_up_dest = parse_chat_ids(self._listener.up_dest)
            print(f"Parsed up_dest: {parsed_up_dest}, type: {type(parsed_up_dest)}")
            
            up_dest_id = parsed_up_dest
            if isinstance(up_dest_id, list) and up_dest_id:
                up_dest_id = up_dest_id[0]  # Take the first item if it's a list
            
            print(f"Processed up_dest_id: {up_dest_id}, type: {type(up_dest_id)}")
            
            # Test if we can use it in a condition
            if up_dest_id != 12345:
                print("up_dest_id != 12345")

# Create an instance and test
listener = Listener()
uploader = TelegramUploader(listener)
uploader.test_up_dest()
