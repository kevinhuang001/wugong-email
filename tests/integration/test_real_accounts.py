import pytest
import os
import argparse
import shutil
import tempfile
from mail import MailManager
from cli import handle_list, handle_sync, handle_read, handle_send, handle_account, handle_delete
from unittest.mock import patch, MagicMock

# 获取加密密码
PASSWORD = os.environ.get("WUGONG_PASSWORD", "123456")

@pytest.fixture(scope="module")
def manager():
    # 为了避免 readonly 数据库问题，我们将 config.toml 和 cache.db 复制到临时目录测试
    temp_dir = tempfile.mkdtemp()
    original_config_dir = "/Users/kevinwong/.config/wugong"
    
    # 复制配置文件
    shutil.copy(os.path.join(original_config_dir, "config.toml"), temp_dir)
    # 尝试复制数据库（如果存在）
    cache_db = os.path.join(original_config_dir, "cache.db")
    if os.path.exists(cache_db):
        shutil.copy(cache_db, temp_dir)
    
    config_path = os.path.join(temp_dir, "config.toml")
    
    yield MailManager(config_path)
    
    # 测试结束后清理临时目录
    shutil.rmtree(temp_dir)

def test_real_account_list(manager):
    """测试 account list 命令"""
    with patch('cli.console') as mock_console:
        args = argparse.Namespace(account_command="list")
        handle_account(args, manager, MagicMock())
        assert mock_console.print.called

@pytest.mark.parametrize("account_name", ["default", "gmail", "outlook"])
def test_real_sync_and_list_variants(manager, account_name):
    """测试真实账户的 sync 和 list 命令的所有参数变体"""
    acc = manager.get_account_by_name(account_name)
    if not acc:
        pytest.skip(f"Account {account_name} not found")

    # 1. 测试 sync --limit 和 sync --all
    with patch('cli.console'), patch('cli.Progress', MagicMock()):
        # sync --limit
        args = argparse.Namespace(account=account_name, limit=1, all=False, password=PASSWORD)
        handle_sync(args, manager)
        
        # sync --all (谨慎使用，这里只同步一个账户)
        # args = argparse.Namespace(account=account_name, limit=None, all=True, password=PASSWORD)
        # handle_sync(args, manager)

    # 2. 测试 list 的各种过滤参数
    with patch('cli.console') as mock_console, \
         patch.object(manager.reader, 'query_emails', wraps=manager.reader.query_emails) as mock_query:
        
        # 测试 --keyword, --from-user, --since, --before, --limit, --all
        args = argparse.Namespace(
            account=account_name,
            keyword="test",
            from_user="test@example.com",
            since="01-Jan-2024",
            before="31-Dec-2026",
            all=False,
            limit=3,
            local=True, # 使用本地以加快速度并避免频繁连接
            password=PASSWORD
        )
        handle_list(args, manager)
        assert mock_console.print.called
        
        # 验证参数是否正确传递给 query_emails
        args_called = mock_query.call_args[1]
        assert args_called['limit'] == 3
        assert args_called['search_criteria']['keyword'] == "test"
        assert args_called['search_criteria']['from'] == "test@example.com"
        assert args_called['search_criteria']['since'] == "01-Jan-2024"
        assert args_called['search_criteria']['before'] == "31-Dec-2026"

    # 3. 测试 list all
    with patch('cli.console') as mock_console:
        args = argparse.Namespace(
            account="all",
            keyword=None,
            from_user=None,
            since=None,
            before=None,
            all=False,
            limit=2,
            local=True,
            password=PASSWORD
        )
        handle_list(args, manager)
        assert mock_console.print.called

@pytest.mark.parametrize("account_name", ["default", "gmail", "outlook"])
def test_real_read_variants(manager, account_name):
    """测试 read 命令的参数变体 (--text, --html)"""
    acc = manager.get_account_by_name(account_name)
    if not acc:
        pytest.skip(f"Account {account_name} not found")

    emails = manager.storage_manager.get_emails_from_cache(acc.get("friendly_name"), limit=1, search_criteria={}, password=PASSWORD)
    if not emails:
        pytest.skip(f"No cached emails for {account_name}")
    
    email_id = emails[0]['id']

    with patch('cli.console') as mock_console:
        # 测试 --text
        args = argparse.Namespace(account=account_name, id=email_id, password=PASSWORD, text=True, html=False)
        handle_read(args, manager)
        
        # 测试 --html
        args = argparse.Namespace(account=account_name, id=email_id, password=PASSWORD, text=False, html=True)
        handle_read(args, manager)
        assert mock_console.print.called

def test_real_send_with_attachments(manager):
    """测试带附件的发送功能"""
    recipient = "2232939442@qq.com"
    account_name = "default" # 使用默认账户测试附件
    acc = manager.get_account_by_name(account_name)
    if not acc:
        pytest.skip(f"Account {account_name} not found")

    # 创建一个临时测试附件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"This is a test attachment.")
        tmp_path = tmp.name

    try:
        with patch('cli.console') as mock_console:
            args = argparse.Namespace(
                account=account_name,
                to=recipient,
                subject="Integration Test with Attachment",
                body="Please find the attached test file.",
                attach=[tmp_path],
                password=PASSWORD
            )
            handle_send(args, manager)
            assert mock_console.print.called
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_real_delete_flow(manager):
    """测试删除流程的参数传递 (使用 Mock confirm 避免真实删除)"""
    account_name = "default"
    acc = manager.get_account_by_name(account_name)
    if not acc:
        pytest.skip(f"Account {account_name} not found")

    with patch('cli.console'), \
         patch('questionary.confirm') as mock_confirm, \
         patch.object(manager.reader, 'delete_email') as mock_delete:
        
        mock_confirm.return_value.ask.return_value = True
        mock_delete.return_value = (True, "Deleted")
        
        args = argparse.Namespace(account=account_name, id="123", password=PASSWORD)
        handle_delete(args, manager)
        
        assert mock_confirm.called
        mock_delete.assert_called_with(acc, PASSWORD, "123")

