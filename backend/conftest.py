"""確保跑測試時不會去建正式站的 /data（在本機通常沒有寫入權限），
一定要在 import app.config 之前設好，所以放在 rootdir 的 conftest.py。"""
import os
import tempfile

os.environ.setdefault("UAA_DATA_DIR", tempfile.mkdtemp(prefix="uaa_test_"))
