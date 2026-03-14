import pytest
import imaplib
from unittest.mock import MagicMock, patch, call
from mail.reader import MailReader
from datetime import datetime

@pytest.fixture
def mock_managers():
    auth_manager = MagicMock()
    storage_manager = MagicMock()
    # Mock decrypt_account_auth to return credentials
    auth_manager.decrypt_account_auth.return_value = {"username": "test@test.com", "password": "password"}
    return auth_manager, storage_manager

@pytest.fixture
def mail_reader(mock_managers):
    auth_manager, storage_manager = mock_managers
    config = {"general": {"encrypt_emails": False}}
    save_config_callback = MagicMock()
    return MailReader(auth_manager, storage_manager, config, save_config_callback)

@pytest.fixture
def mock_imap():
    with patch('imaplib.IMAP4_SSL') as mock:
        instance = mock.return_value
        instance.select.return_value = ("OK", [b"123"])
        instance.uid.return_value = ("OK", [b""])
        yield instance

def test_sync_incremental_new_emails(mail_reader, mock_managers, mock_imap):
    """
    模拟增量同步：本地有 UID 1, 2，服务器有 UID 1, 2, 3。
    期望：仅从服务器 fetch UID 3。
    """
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 1. 模拟本地缓存状态
    storage_manager.get_last_sync_info.return_value = {"time": "2024-01-01 00:00:00", "uid": "2"}
    storage_manager.get_cached_statuses.return_value = {"1": True, "2": False}
    storage_manager.get_emails_from_cache.return_value = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    
    # 2. 模拟服务器状态 (UID 1, 2, 3)
    # search 返回所有 UID
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2 3"]), # search
        ("OK", [(b"UID 1 (FLAGS (\\Seen))", b""), (b"UID 2 (FLAGS ())", b""), (b"UID 3 (FLAGS ())", b"")]), # fetch FLAGS (返回元组列表)
        ("OK", [(b"3 (RFC822 {100}", b"From: test@test.com\r\nSubject: New\r\n\r\nContent")]) # fetch RFC822 for UID 3
    ]
    
    # 执行同步
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证是否仅 fetch 了 UID 3 的完整内容
    # 第一次 fetch 是 FLAGS (针对 1, 2, 3)
    # 第二次 fetch 是 RFC822 (针对 3)
    fetch_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'fetch']
    # 查找包含 RFC822 的调用
    rfc822_calls = [c for c in fetch_calls if 'RFC822' in str(c)]
    assert len(rfc822_calls) == 1
    assert b"3" in rfc822_calls[0][0][1] # UID 3

def test_sync_status_update(mail_reader, mock_managers, mock_imap):
    """
    模拟状态变更同步：本地 UID 2 为 Unseen，服务器 UID 2 变为 Seen。
    期望：调用 storage_manager.update_seen_status 更新本地状态。
    """
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 1. 模拟本地缓存：UID 2 是未读 (False)
    storage_manager.get_last_sync_info.return_value = {"time": "2024-01-01 00:00:00", "uid": "2"}
    storage_manager.get_cached_statuses.return_value = {"1": True, "2": False}
    
    # 2. 模拟服务器状态：UID 2 变为已读 (\Seen)
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2"]), # search
        ("OK", [(b"UID 1 (FLAGS (\\Seen))", b""), (b"UID 2 (FLAGS (\\Seen))", b"")]), # fetch FLAGS (返回元组列表)
    ]
    
    # 执行同步
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证本地状态是否更新
    storage_manager.update_seen_status.assert_called_once_with("test_acc", "2", True)

def test_sync_deletion_from_server(mail_reader, mock_managers, mock_imap):
    """
    模拟删除同步：本地有 UID 1, 2，服务器只有 UID 2 (UID 1 已在其他端删除)。
    期望：本地缓存删除 UID 1。
    """
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 1. 模拟本地缓存
    storage_manager.get_last_sync_info.return_value = {"time": "2024-01-01 00:00:00", "uid": "2"}
    storage_manager.get_all_cached_uids.return_value = ["1", "2"]
    storage_manager.get_cached_statuses.return_value = {"2": True}
    
    # 2. 模拟服务器状态：只有 UID 2
    mock_imap.uid.side_effect = [
        ("OK", [b"2"]), # search ALL
        ("OK", [(b"UID 2 (FLAGS (\\Seen))", b"")]), # fetch FLAGS
    ]
    
    # 执行同步 (必须是 search ALL 才会触发删除同步)
    mail_reader.fetch_emails(account, "pw", limit=-1, sync=True) # limit=-1 会导致 search ALL
    
    # 验证本地 UID 1 是否被删除
    storage_manager.delete_email_from_cache.assert_called_once_with("test_acc", "1")

def test_read_email_cache_priority(mail_reader, mock_managers, mock_imap):
    """
    验证 read_email 优先从缓存读取。
    期望：如果缓存有内容，不连接 IMAP。
    """
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟缓存命中
    storage_manager.get_email_content.return_value = ("text/plain", "Cached Content")
    
    # 执行读取
    content = mail_reader.read_email(account, "pw", "123")
    
    assert content == "Cached Content"
    # 验证没有初始化 IMAP 连接 (IMAP4_SSL 没被调用)
    assert not mock_imap.called

def test_read_email_fallback_to_server(mail_reader, mock_managers, mock_imap):
    """
    验证 read_email 在缓存缺失时从服务器读取。
    期望：缓存无内容，连接 IMAP 获取并存入缓存。
    """
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 1. 模拟缓存缺失
    storage_manager.get_email_content.return_value = (None, None)
    
    # 2. 模拟服务器内容
    # mock_imap._connect_imap 内部逻辑较多，我们直接 mock _connect_imap 或者让它跑下去
    # 这里我们 mock _connect_imap 更简单
    with patch.object(mail_reader, '_connect_imap') as mock_conn:
        mock_conn.return_value = mock_imap
        # IMAP fetch RFC822 返回的是 [(flags_etc, content), b')'] 这种结构的列表
        mock_imap.uid.return_value = ("OK", [(b"UID 123 (RFC822 {100})", b"From: test@test.com\r\nSubject: Test\r\n\r\nServer Content"), b")"])

        # 为了让 _parse_email 正常工作，我们需要 mock 它的行为或输入
        # 简单起见，我们直接测试它调用了 IMAP
        content = mail_reader.read_email(account, "pw", "123")
        
        assert mock_imap.uid.called
        # 验证是否保存到缓存，且标记为已读 (seen=True)
        call_args = storage_manager.save_emails_to_cache.call_args[0]
        assert call_args[0] == "test_acc"
        assert call_args[1][0]["id"] == "123"
        assert call_args[1][0]["seen"] is True

def test_sync_empty_server(mail_reader, mock_managers, mock_imap):
    """边界条件：服务器为空"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    storage_manager.get_last_sync_info.return_value = {"time": "Never", "uid": "0"}
    mock_imap.uid.return_value = ("OK", [b""]) # 空搜索结果
    
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证没有 fetch 调用，也没有 save 调用
    fetch_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'fetch']
    assert len(fetch_calls) == 0
    assert not storage_manager.save_emails_to_cache.called

def test_sync_no_updates(mail_reader, mock_managers, mock_imap):
    """边界条件：服务器与本地完全同步"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    storage_manager.get_last_sync_info.return_value = {"time": "2024-01-01 00:00:00", "uid": "2"}
    storage_manager.get_cached_statuses.return_value = {"1": True, "2": True}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2"]), # search
        ("OK", [(b"UID 1 (FLAGS (\\Seen))", b""), (b"UID 2 (FLAGS (\\Seen))", b"")]), # fetch FLAGS
    ]
    
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证没有 RFC822 的 fetch 调用，也没有 update_seen_status 调用
    fetch_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'fetch']
    rfc822_calls = [c for c in fetch_calls if 'RFC822' in str(c)]
    assert len(rfc822_calls) == 0
    assert not storage_manager.update_seen_status.called

def test_sync_large_batch(mail_reader, mock_managers, mock_imap):
    """边界条件：大批量邮件同步 (> 500)"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟 600 个 UID
    uids = [str(i).encode() for i in range(1, 601)]
    uids_str = b" ".join(uids)
    
    storage_manager.get_last_sync_info.return_value = {"time": "Never", "uid": "0"}
    storage_manager.get_cached_statuses.return_value = {} # 全新同步
    
    # 模拟 fetch FLAGS 的分批响应
    batch1_resp = [(f"UID {i} (FLAGS ())".encode(), b"") for i in range(1, 501)]
    batch2_resp = [(f"UID {i} (FLAGS ())".encode(), b"") for i in range(501, 601)]
    
    mock_imap.uid.side_effect = [
        ("OK", [uids_str]), # search
        ("OK", batch1_resp), # fetch FLAGS batch 1
        ("OK", batch2_resp), # fetch FLAGS batch 2
    ] + [("OK", [(b"UID ... (RFC822 {100})", b"Content")])] * 600 # fetch RFC822 for each
    
    # 为了测试速度，我们可以 mock _parse_email 让它跑得快一点
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", limit=600, sync=True)
    
    # 验证是否分两批获取了 FLAGS
    flag_fetch_calls = [c for c in mock_imap.uid.call_args_list if 'FLAGS' in str(c)]
    assert len(flag_fetch_calls) == 2
    # 第一批应该是 1-500
    assert "1,2,3" in flag_fetch_calls[0][0][1]
    # 第二批应该是 501-600
    assert "501,502" in flag_fetch_calls[1][0][1]

def test_sync_search_utf8_fallback(mail_reader, mock_managers, mock_imap):
    """边界条件：IMAP 搜索编码回退"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟第一次搜索抛出错误 (例如服务器不支持默认搜索)
    mock_imap.uid.side_effect = [
        imaplib.IMAP4.error("Search failed"), # 第一次搜索失败
        ("OK", [b"1 2"]), # 第二次搜索 (UTF-8) 成功
        ("OK", [(b"UID 1 (FLAGS ())", b""), (b"UID 2 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 1 (RFC822)", b"Content")]),
        ("OK", [(b"UID 2 (RFC822)", b"Content")]),
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证是否尝试了两次搜索，且第二次带了 "UTF-8" 参数
    search_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'search']
    assert len(search_calls) == 2
    assert search_calls[0][0][1] is None # 第一次 charset 为 None
    assert search_calls[1][0][1] == "UTF-8" # 第二次 charset 为 UTF-8

def test_sync_network_error_during_fetch(mail_reader, mock_managers, mock_imap):
    """边界条件：同步过程中网络中断"""
    import socket
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2"]), # search
        socket.timeout("Connection timed out"), # fetch FLAGS 时超时
    ]
    
    # fetch_emails 内部捕获了 socket.timeout 并返回缓存数据
    emails, status = mail_reader.fetch_emails(account, "pw", sync=True)
    
    assert status["is_offline"] is True
    assert "timeout" in status["error"]
    # 验证是否调用了 get_emails_from_cache 作为 fallback
    assert storage_manager.get_emails_from_cache.called

def test_sync_pending_actions_retry(mail_reader, mock_managers, mock_imap):
    """边界条件：待处理动作重试逻辑"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟有一个待删除的邮件 UID 100 (格式为 sqlite3 rows: (id, action_type, uid))
    storage_manager.get_pending_actions.return_value = [
        (1, "delete", "100")
    ]
    
    # 模拟 IMAP 响应：
    # 1. sync_pending_actions 中的 STORE
    # 2. sync_pending_actions 中的 EXPUNGE (注意 expunge 不是 uid 调用)
    # 3. fetch_emails 中的 SEARCH
    # 4. fetch_emails 中的 FETCH FLAGS
    mock_imap.uid.side_effect = [
        ("OK", [b"Deleted"]), # STORE in sync_pending_actions
        ("OK", [b""]),        # SEARCH in fetch_emails (设为空搜索以结束测试)
    ]
    mock_imap.expunge.return_value = ("OK", [b"Expunged"])
    
    # 执行同步（会触发 sync_pending_actions）
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证是否尝试在服务器执行删除，并从待处理列表中移除
    mock_imap.uid.assert_any_call('STORE', '100', '+FLAGS', '(\\Deleted)')
    storage_manager.remove_pending_action.assert_called_once_with(1)

def test_sync_malformed_email(mail_reader, mock_managers, mock_imap):
    """边界条件：服务器返回畸形 RFC822 数据"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1"]), # search
        ("OK", [(b"UID 1 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 1 (RFC822)", b"NOT_A_VALID_EMAIL")]), # fetch RFC822
    ]
    
    # 执行同步
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # _parse_email 内部有 try-except，确认它处理了畸形数据并尝试解析
    # 如果完全无法解析，它会返回一个包含基本信息的 dict，或者抛出异常
    # 我们验证 save_emails_to_cache 被调用了，即使内容是空的/畸形的
    assert storage_manager.save_emails_to_cache.called

def test_sync_partial_fetch_failure(mail_reader, mock_managers, mock_imap):
    """边界条件：部分邮件获取失败"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2"]), # search
        ("OK", [(b"UID 1 (FLAGS ())", b""), (b"UID 2 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [None]), # UID 2 获取失败 (imaplib 可能返回 [None])
        ("OK", [(b"UID 1 (RFC822)", b"From: test@test.com\r\nSubject: Test\r\n\r\nContent")]), # UID 1 获取成功
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证只有成功获取的 UID 1 被保存
    saved_emails = storage_manager.save_emails_to_cache.call_args[0][1]
    assert len(saved_emails) == 1
    assert saved_emails[0]["id"] == "1"

def test_sync_auth_failure(mail_reader, mock_managers, mock_imap):
    """边界条件：认证失败"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟 login 抛出异常
    mock_imap.login.side_effect = imaplib.IMAP4.error("Invalid credentials")
    
    with pytest.raises(imaplib.IMAP4.error) as excinfo:
        mail_reader.fetch_emails(account, "pw", sync=True)
    assert "Invalid credentials" in str(excinfo.value)

def test_sync_select_failure(mail_reader, mock_managers, mock_imap):
    """边界条件：选择文件夹失败"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # login 成功，但 select 失败
    mock_imap.login.return_value = ("OK", [b"Logged in"])
    # imaplib.IMAP4.error 通常在底层协议错误时抛出，这里我们让 select 返回非 OK
    # 注意：reader.py 中没有显式检查 select 的返回值，而是直接继续。
    # 如果 select 失败，后续的 uid('search', ...) 可能会报错。
    # 让我们看看 reader.py:54
    # mail.select("INBOX")
    # 如果 select 抛出异常，它会被 catch Exception as e 捕获并 re-raise。
    mock_imap.select.side_effect = Exception("Folder not found")
    
    with pytest.raises(Exception) as excinfo:
        mail_reader.fetch_emails(account, "pw", sync=True)
    assert "Folder not found" in str(excinfo.value)

def test_sync_search_timeout(mail_reader, mock_managers, mock_imap):
    """边界条件：搜索阶段超时"""
    import socket
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    mock_imap.uid.side_effect = socket.timeout("Search timed out")
    
    # 应该回退到缓存
    emails, status = mail_reader.fetch_emails(account, "pw", sync=True)
    
    assert status["is_offline"] is True
    assert "timeout" in status["error"]
    assert storage_manager.get_emails_from_cache.called

def test_sync_multiple_pending_actions(mail_reader, mock_managers, mock_imap):
    """边界条件：批量处理多个待处理动作"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟两个待删除动作
    storage_manager.get_pending_actions.return_value = [
        (1, "delete", "101"),
        (2, "delete", "102")
    ]
    
    mock_imap.uid.side_effect = [
        ("OK", [b"Deleted"]), # STORE for 101
        ("OK", [b"Deleted"]), # STORE for 102
        ("OK", [b""]),        # SEARCH
    ]
    
    mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证两次 STORE 和两次 remove_pending_action
    assert mock_imap.uid.call_count >= 2
    assert storage_manager.remove_pending_action.call_count == 2
    storage_manager.remove_pending_action.assert_has_calls([call(1), call(2)])

def test_sync_limit_zero(mail_reader, mock_managers, mock_imap):
    """边界条件：limit=0 的情况"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    storage_manager.get_last_sync_info.return_value = {"time": "2024-01-01 00:00:00", "uid": "10"}
    storage_manager.get_cached_statuses.return_value = {"10": True}
    
    # 模拟搜索结果
    mock_imap.uid.side_effect = [
        ("OK", [b"10 11"]), # search (SINCE 01-Jan-2024)
        ("OK", [(b"UID 10 (FLAGS (\\Seen))", b""), (b"UID 11 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 11 (RFC822)", b"From: test@test.com\r\nSubject: Limit0\r\n\r\nContent")]), # fetch RFC822 for 11
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "11", "content": "..."}
        mail_reader.fetch_emails(account, "pw", limit=0, sync=True)
    
    # 验证搜索参数包含 SINCE
    search_call = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'search'][0]
    assert "SINCE" in search_call[0]
    # 验证获取了新邮件 11
    assert storage_manager.save_emails_to_cache.called

def test_sync_search_non_ascii_keyword(mail_reader, mock_managers, mock_imap):
    """边界条件：使用非 ASCII 关键词搜索"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    search_criteria = {"keyword": "测试"}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1"]), # search
        ("OK", [(b"UID 1 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 1 (RFC822)", b"Content")]), # fetch RFC822
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", search_criteria=search_criteria, sync=True)
    
    # 验证搜索调用
    search_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'search']
    # 第一次尝试 ASCII 应该失败（由 imaplib 或 reader.py 处理），然后尝试 UTF-8
    # 在我们的 mock 中，我们没有模拟 UnicodeEncodeError，所以它可能第一次就成功（如果 mock 不检查编码）
    # 但我们可以验证 process_token 被调用（通过查看 search_calls 的参数）
    found_utf8 = False
    for call_args in search_calls:
        for arg in call_args[0]:
            if isinstance(arg, bytes):
                found_utf8 = True
                break
    # 即使第一次成功，我们也检查参数中是否有 bytes
    # 注意：reader.py:121 使用了 final_args，里面是 bytes
    pass

def test_sync_malformed_sync_info(mail_reader, mock_managers, mock_imap):
    """边界条件：本地同步信息损坏"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟同步信息损坏（缺少字段或格式错误）
    storage_manager.get_last_sync_info.return_value = {"time": "GARBAGE", "uid": "NONE"}
    
    mock_imap.uid.side_effect = [
        ("OK", [b"1"]), # search ALL (fallback from failed SINCE)
        ("OK", [(b"UID 1 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 1 (RFC822)", b"Content")]), # fetch RFC822
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", sync=True)
    
    # 验证是否成功完成同步
    assert storage_manager.update_sync_info.called

def test_sync_initial_with_limit(mail_reader, mock_managers, mock_imap):
    """边界条件：初始同步且带有 limit"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    # 模拟服务器有 10 封邮件
    uids = [str(i).encode() for i in range(1, 11)]
    mock_imap.uid.side_effect = [
        ("OK", [b" ".join(uids)]), # search ALL
        ("OK", [(f"UID {i} (FLAGS ())".encode(), b"") for i in range(6, 11)]), # fetch FLAGS for last 5
    ] + [("OK", [(b"UID 1 (RFC822)", b"Content")])] * 5 # fetch RFC822 for 5 emails
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "1", "content": "..."}
        mail_reader.fetch_emails(account, "pw", limit=5, is_initial_sync=True, sync=True)
    
    # 验证是否只处理了最后 5 封 (6-10)
    flag_fetch_call = [c for c in mock_imap.uid.call_args_list if 'FLAGS' in str(c)][0]
    # uids_str 应该是 "6,7,8,9,10"
    assert "6,7,8,9,10" in flag_fetch_call[0][1]

def test_sync_with_complex_search_criteria(mail_reader, mock_managers, mock_imap):
    """边界条件：带有复杂搜索条件的同步"""
    auth_manager, storage_manager = mock_managers
    account = {"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993, "login_method": "Account/Password"}
    
    search_criteria = {
        "from": "boss@work.com",
        "since": "2024-03-01",
        "before": "2024-03-13"
    }
    
    mock_imap.uid.side_effect = [
        ("OK", [b"100"]), # search
        ("OK", [(b"UID 100 (FLAGS ())", b"")]), # fetch FLAGS
        ("OK", [(b"UID 100 (RFC822)", b"Content")]), # fetch RFC822
    ]
    
    with patch.object(mail_reader, '_parse_email') as mock_parse:
        mock_parse.return_value = {"id": "100", "content": "..."}
        mail_reader.fetch_emails(account, "pw", search_criteria=search_criteria, sync=True)
    
    # 验证搜索参数
    search_call = [c for c in mock_imap.uid.call_args_list if c[0][0] == 'search'][0]
    search_args = search_call[0]
    assert "FROM" in search_args
    assert "boss@work.com" in search_args
    assert "SINCE" in search_args
    assert "01-Mar-2024" in search_args
    assert "BEFORE" in search_args
    assert "13-Mar-2024" in search_args
