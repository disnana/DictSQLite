#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ベンチマーク結果のバージョン管理システム

バージョンごとに固定の名前でCSVと画像を保存し、
複数バージョン間の比較を容易にします。
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import shutil

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'))


class VersionManager:
    """ベンチマーク結果のバージョン管理クラス"""
    
    def __init__(self, results_dir: Path = None):
        """
        Args:
            results_dir: 結果を保存するディレクトリ（デフォルト: others/benchmark/results）
        """
        if results_dir is None:
            results_dir = BASE_DIR / "results"
        
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # バージョンごとの結果ディレクトリ
        self.version_results_dir = self.results_dir / "versions"
        self.version_results_dir.mkdir(exist_ok=True)
        
        # 比較グラフディレクトリ
        self.comparison_dir = self.results_dir / "comparisons"
        self.comparison_dir.mkdir(exist_ok=True)
        
        # バージョン情報ファイル
        self.version_info_file = self.results_dir / "version_history.json"
        self._load_version_history()
    
    def _load_version_history(self):
        """バージョン履歴を読み込む"""
        if self.version_info_file.exists():
            with open(self.version_info_file, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)
        else:
            self.version_history = {
                'versions': {},
                'latest_run': None
            }
    
    def _save_version_history(self):
        """バージョン履歴を保存"""
        with open(self.version_info_file, 'w', encoding='utf-8') as f:
            json.dump(self.version_history, f, indent=2, ensure_ascii=False)
    
    def get_version_info(self) -> Dict[str, str]:
        """各パッケージのバージョン情報を取得"""
        versions = {}
        
        try:
            # まずインポートを試みる
            import dictsqlite.main
            versions['original'] = dictsqlite.main.__version__
        except ImportError as e:
            # モジュールが見つからない場合はファイルから直接読み込む
            try:
                version_file = REPO_ROOT / 'dictsqlite' / 'main.py'
                if version_file.exists():
                    with open(version_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if '__version__' in line and '=' in line:
                                # __version__ = '1.8.9' の形式を抽出
                                parts = line.split('=')[1].strip()
                                # コメントを除去
                                if '#' in parts:
                                    parts = parts.split('#')[0].strip()
                                version_str = parts.strip("'\"")
                                versions['original'] = version_str
                                break
                else:
                    versions['original'] = 'unknown'
            except Exception:
                versions['original'] = 'unknown'
        except Exception as e:
            print(f"⚠ Original版のバージョン取得失敗: {e}")
            versions['original'] = 'unknown'
        
        try:
            import dictsqlite_fastest
            versions['fastest'] = dictsqlite_fastest.__version__
        except ImportError:
            # ファイルから直接読み込む
            try:
                version_file = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'dictsqlite_fastest' / '__init__.py'
                if version_file.exists():
                    with open(version_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if '__version__' in line and '=' in line:
                                parts = line.split('=')[1].strip()
                                if '#' in parts:
                                    parts = parts.split('#')[0].strip()
                                version_str = parts.strip("'\"")
                                versions['fastest'] = version_str
                                break
                else:
                    versions['fastest'] = 'unknown'
            except Exception:
                versions['fastest'] = 'unknown'
        except Exception as e:
            print(f"⚠ Fastest版のバージョン取得失敗: {e}")
            versions['fastest'] = 'unknown'
        
        try:
            import dictsqlite_fastest_beta
            versions['beta'] = dictsqlite_fastest_beta.__version__
        except ImportError:
            # ファイルから直接読み込む
            try:
                version_file = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta' / '__init__.py'
                if version_file.exists():
                    with open(version_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if '__version__' in line and '=' in line:
                                parts = line.split('=')[1].strip()
                                if '#' in parts:
                                    parts = parts.split('#')[0].strip()
                                version_str = parts.strip("'\"")
                                versions['beta'] = version_str
                                break
                else:
                    versions['beta'] = 'unknown'
            except Exception:
                versions['beta'] = 'unknown'
        except Exception as e:
            print(f"⚠ Beta版のバージョン取得失敗: {e}")
            versions['beta'] = 'unknown'
        
        return versions
    
    def get_version_string(self) -> str:
        """複合バージョン文字列を生成（例: v1.8.9_v1.0.0_v0.1.0-beta）"""
        versions = self.get_version_info()
        return f"v{versions['original']}_v{versions['fastest']}_v{versions['beta']}"
    
    def get_version_paths(self, version_string: str = None) -> Dict[str, Path]:
        """バージョン固有のファイルパスを取得
        
        Args:
            version_string: バージョン文字列（Noneの場合は現在のバージョンを使用）
            
        Returns:
            各ファイルタイプのパスを含む辞書
        """
        if version_string is None:
            version_string = self.get_version_string()
        
        version_dir = self.version_results_dir / version_string
        version_dir.mkdir(exist_ok=True)
        
        return {
            'dir': version_dir,
            'csv': version_dir / f"benchmark_{version_string}.csv",
            'json': version_dir / f"benchmark_{version_string}.json",
            'summary': version_dir / f"summary_{version_string}.md",
            'log': version_dir / f"benchmark_{version_string}.log",
            'graphs_dir': version_dir / "graphs"
        }
    
    def save_benchmark_result(
        self,
        csv_content: str = None,
        json_content: dict = None,
        summary_content: str = None,
        log_content: str = None,
        version_string: str = None
    ) -> Dict[str, Path]:
        """ベンチマーク結果をバージョン固有のファイルとして保存
        
        Args:
            csv_content: CSVファイルの内容（文字列）
            json_content: JSONデータ（辞書）
            summary_content: サマリーファイルの内容（文字列）
            log_content: ログファイルの内容（文字列）
            version_string: バージョン文字列（Noneの場合は現在のバージョンを使用）
            
        Returns:
            保存されたファイルのパス辞書
        """
        if version_string is None:
            version_string = self.get_version_string()
        
        paths = self.get_version_paths(version_string)
        saved_files = {}
        
        # CSVを保存
        if csv_content is not None:
            with open(paths['csv'], 'w', encoding='utf-8') as f:
                f.write(csv_content)
            saved_files['csv'] = paths['csv']
            print(f"✓ CSV保存: {paths['csv']}")
        
        # JSONを保存
        if json_content is not None:
            with open(paths['json'], 'w', encoding='utf-8') as f:
                json.dump(json_content, f, indent=2, ensure_ascii=False)
            saved_files['json'] = paths['json']
            print(f"✓ JSON保存: {paths['json']}")
        
        # サマリーを保存
        if summary_content is not None:
            with open(paths['summary'], 'w', encoding='utf-8') as f:
                f.write(summary_content)
            saved_files['summary'] = paths['summary']
            print(f"✓ サマリー保存: {paths['summary']}")
        
        # ログを保存
        if log_content is not None:
            with open(paths['log'], 'w', encoding='utf-8') as f:
                f.write(log_content)
            saved_files['log'] = paths['log']
            print(f"✓ ログ保存: {paths['log']}")
        
        # バージョン履歴を更新
        timestamp = datetime.now().isoformat()
        if version_string not in self.version_history['versions']:
            self.version_history['versions'][version_string] = []
        
        self.version_history['versions'][version_string].append({
            'timestamp': timestamp,
            'files': [str(p) for p in saved_files.values()]
        })
        self.version_history['latest_run'] = timestamp
        self._save_version_history()
        
        return saved_files
    
    def copy_graphs_to_version(
        self,
        graphs_source_dir: Path,
        version_string: str = None
    ) -> Path:
        """グラフをバージョン固有のディレクトリにコピー
        
        Args:
            graphs_source_dir: ソースグラフディレクトリ
            version_string: バージョン文字列（Noneの場合は現在のバージョンを使用）
            
        Returns:
            コピー先のディレクトリパス
        """
        if version_string is None:
            version_string = self.get_version_string()
        
        paths = self.get_version_paths(version_string)
        graphs_dest_dir = paths['graphs_dir']
        graphs_dest_dir.mkdir(exist_ok=True)
        
        if graphs_source_dir.exists():
            # 既存のグラフを削除（上書き）
            if graphs_dest_dir.exists():
                for file in graphs_dest_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
            
            # グラフをコピー
            copied_count = 0
            for graph_file in graphs_source_dir.glob('*.png'):
                dest_file = graphs_dest_dir / graph_file.name
                shutil.copy2(graph_file, dest_file)
                copied_count += 1
            
            for graph_file in graphs_source_dir.glob('*.html'):
                dest_file = graphs_dest_dir / graph_file.name
                shutil.copy2(graph_file, dest_file)
                copied_count += 1
            
            print(f"✓ グラフコピー: {copied_count}個のファイルを {graphs_dest_dir} にコピー")
        
        return graphs_dest_dir
    
    def list_available_versions(self) -> List[str]:
        """利用可能なバージョン一覧を取得"""
        versions = []
        if self.version_results_dir.exists():
            for version_dir in self.version_results_dir.iterdir():
                if version_dir.is_dir() and version_dir.name.startswith('v'):
                    versions.append(version_dir.name)
        return sorted(versions)
    
    def get_version_metadata(self, version_string: str) -> Optional[dict]:
        """特定バージョンのメタデータを取得"""
        return self.version_history['versions'].get(version_string)
    
    def create_comparison_report(self, version_strings: List[str] = None) -> Path:
        """複数バージョンの比較レポートを作成
        
        Args:
            version_strings: 比較するバージョンのリスト（Noneの場合は全バージョン）
            
        Returns:
            作成されたレポートファイルのパス
        """
        if version_strings is None:
            version_strings = self.list_available_versions()
        
        if not version_strings:
            print("⚠ 比較可能なバージョンがありません")
            return None
        
        # 比較レポートを作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.comparison_dir / f"comparison_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# ベンチマーク バージョン比較レポート\n\n")
            f.write(f"**作成日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**比較バージョン数:** {len(version_strings)}\n\n")
            
            f.write("## 比較対象バージョン\n\n")
            for i, version in enumerate(version_strings, 1):
                metadata = self.get_version_metadata(version)
                f.write(f"{i}. **{version}**\n")
                if metadata:
                    latest_run = metadata[-1] if metadata else None
                    if latest_run:
                        f.write(f"   - 最終実行: {latest_run['timestamp']}\n")
                f.write("\n")
            
            f.write("## ファイル場所\n\n")
            for version in version_strings:
                paths = self.get_version_paths(version)
                f.write(f"### {version}\n\n")
                f.write(f"- CSV: `{paths['csv'].relative_to(self.results_dir.parent)}`\n")
                f.write(f"- JSON: `{paths['json'].relative_to(self.results_dir.parent)}`\n")
                f.write(f"- グラフ: `{paths['graphs_dir'].relative_to(self.results_dir.parent)}/`\n")
                f.write("\n")
        
        print(f"✓ 比較レポート作成: {report_path}")
        return report_path
    
    def cleanup_old_versions(self, keep_latest: int = 5):
        """古いバージョンの結果を削除
        
        Args:
            keep_latest: 保持する最新バージョン数
        """
        versions = self.list_available_versions()
        
        if len(versions) <= keep_latest:
            print(f"✓ 削除対象なし（保持数: {len(versions)}、上限: {keep_latest}）")
            return
        
        # 古いバージョンを削除
        versions_to_delete = versions[:-keep_latest]
        for version in versions_to_delete:
            version_dir = self.version_results_dir / version
            if version_dir.exists():
                shutil.rmtree(version_dir)
                print(f"✓ 削除: {version}")
                
                # 履歴からも削除
                if version in self.version_history['versions']:
                    del self.version_history['versions'][version]
        
        self._save_version_history()
        print(f"✓ {len(versions_to_delete)}個のバージョンを削除しました")


def main():
    """テスト実行"""
    manager = VersionManager()
    
    print("=" * 80)
    print("バージョン管理システム テスト")
    print("=" * 80)
    
    # バージョン情報取得
    versions = manager.get_version_info()
    print(f"\n現在のバージョン:")
    for name, version in versions.items():
        print(f"  {name}: {version}")
    
    version_string = manager.get_version_string()
    print(f"\nバージョン文字列: {version_string}")
    
    # パス取得
    paths = manager.get_version_paths()
    print(f"\n保存先パス:")
    for key, path in paths.items():
        if key != 'dir':
            print(f"  {key}: {path}")
    
    # 利用可能なバージョン一覧
    available = manager.list_available_versions()
    print(f"\n利用可能なバージョン: {len(available)}個")
    for version in available:
        print(f"  - {version}")


if __name__ == '__main__':
    main()
