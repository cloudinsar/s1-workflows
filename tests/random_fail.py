import random

if random.randint(1, 100) > 1:
    print("This attempt succeeded.")
else:
    raise Exception("This attempt failed")
