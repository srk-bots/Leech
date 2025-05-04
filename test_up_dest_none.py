class Listener:
    def __init__(self):
        self.up_dest = None
        
class TelegramUploader:
    def __init__(self, listener):
        self._listener = listener
        
    def test_up_dest(self):
        # Test if up_dest is None
        print(f"Original up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Test the condition
        if self._listener.up_dest is not None and self._listener.up_dest:
            print("up_dest is not None and not empty")
        else:
            print("up_dest is None or empty")
            
        # Test with an empty string
        self._listener.up_dest = ""
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Test the condition
        if self._listener.up_dest is not None and self._listener.up_dest:
            print("up_dest is not None and not empty")
        else:
            print("up_dest is None or empty")
            
        # Test with a non-empty string
        self._listener.up_dest = "123456789"
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Test the condition
        if self._listener.up_dest is not None and self._listener.up_dest:
            print("up_dest is not None and not empty")
        else:
            print("up_dest is None or empty")
            
        # Test with a list
        self._listener.up_dest = [123456789]
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Test the condition
        if self._listener.up_dest is not None and self._listener.up_dest:
            print("up_dest is not None and not empty")
        else:
            print("up_dest is None or empty")
            
        # Test with an empty list
        self._listener.up_dest = []
        print(f"\nOriginal up_dest: {self._listener.up_dest}, type: {type(self._listener.up_dest)}")
        
        # Test the condition
        if self._listener.up_dest is not None and self._listener.up_dest:
            print("up_dest is not None and not empty")
        else:
            print("up_dest is None or empty")

# Create an instance and test
listener = Listener()
uploader = TelegramUploader(listener)
uploader.test_up_dest()
