# SeedrClient

SeedrClient is a simple python library that interfaces with Seedr. However, unlike the offical
rest API, to use SeedrClient you do not need a premium account and even free users can access
the API.

It is based on [@theabbie](https://github.com/theabbie/seedr-api) and
[@hemantapkh](https://github.com/hemantapkh/seedrcc) work.

### Installation
```shell
pip install SeedrClient
```

### Example code
```python
from seedr_client import SeedrHandler


seedr = SeedrHandler(email="youremail@example.com", password="your_password")
print(seedr.get_drive())
# Should return a similar result
# {'space': {'total': '5.0 GB', 'used': '1.1 GB'}, 'parent_folder_id': 123456789,
# 'torrents': [], 'folders': [{'folder_id': 123456799, 'folder_name':
# 'Ubuntu Minimal ISO 22.04 Custom', 'size': '1.1 GB'}], 'files': []}
```

### Documentation
You can find the documentation for SeedrClient over [here](https://seedrclient.readthedocs.io/)

### TODO
- [ ] Reuse access token
- [ ] Refresh access token when it expires
- [ ] Add error notification via Telegram
- [ ] Build a command line interface
- [ ] Build a GUI app to monitor all SeedrClient activities