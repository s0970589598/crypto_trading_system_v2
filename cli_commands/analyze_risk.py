"""
量化風險分析 CLI 命令

提供命令行接口來執行量化風險分析，包括：
- Kelly Criterion 計算
- 傾斜行為檢測
- 破產風險分析
- 手續費壓力分析
- 恢復係數計算
- 情緒控制分析
- 能力維度評分
- 最長連損分析
- 短線交易分析
- 冷靜期建議
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer


logger = logging.getLogger(__name__)


# 分析類型映射
ANALYSIS_TYPES = {
    'all': '所有分析',
    'kelly': 'Kelly Criterion',
    'tilt': '傾斜行為檢測',
    'ror': '破產風險',
    'fee': '手續費壓力',
    'recovery': '恢復係數',
    'emotional': '情緒控制',
    'skill': '能力評分',
    'streak': '最長連損',
    'short': '短線交易分析',
    'cooling': '冷靜期建議',
}


def load_trades_data(data_path: str) -> QuantitativeRiskAnalyzer:
    """
    載入交易數據並創建分析器
    
    Args:
        data_path: 交易數據文件路徑
    
    Returns:
        QuantitativeRiskAnalyzer: 量化風險分析器實例
    
    Raises:
        FileNotFoundError: 數據文件不存在
        ValueError: 數據格式錯誤
    """
    data_file = Path(data_path)
    
    if not data_file.exists():
        raise FileNotFoundError(f"數據文件不存在：{data_path}")
    
    try:
        analyzer = QuantitativeRiskAnalyzer(data_path)
        logger.info(f"成功載入交易數據：{data_path}")
        return analyzer
    
    except Exception as e:
        raise ValueError(f"載入數據失敗：{e}")


def analyze_kelly(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行 Kelly Criterion 分析"""
    return analyzer.calculate_ror_kelly()


def analyze_tilt(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行傾斜行為檢測"""
    return analyzer.detect_tilt_behavior()


def analyze_ror(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行破產風險分析"""
    return analyzer.calculate_risk_of_ruin()


def analyze_fee(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行手續費壓力分析"""
    return analyzer.calculate_fee_pressure()


def analyze_recovery(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行恢復係數分析"""
    return analyzer.calculate_recovery_factor()


def analyze_emotional(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行情緒控制分析"""
    return analyzer.analyze_emotional_control()


def analyze_skill(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行能力評分分析"""
    return analyzer.calculate_skill_dimensions()


def analyze_streak(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行最長連損分析"""
    return analyzer.calculate_max_losing_streak()


def analyze_short(analyzer: QuantitativeRiskAnalyzer, minutes: float) -> Dict[str, Any]:
    """執行短線交易分析"""
    return analyzer.analyze_short_term_trades(minutes)


def analyze_cooling(analyzer: QuantitativeRiskAnalyzer) -> Dict[str, Any]:
    """執行冷靜期分析"""
    return analyzer.check_cooling_period()


def analyze_all(analyzer: QuantitativeRiskAnalyzer, short_minutes: float) -> Dict[str, Any]:
    """
    執行所有分析
    
    Args:
        analyzer: 量化風險分析器
        short_minutes: 短線交易時間閾值
    
    Returns:
        Dict[str, Any]: 所有分析結果
    """
    results = {}
    
    try:
        results['kelly_criterion'] = analyze_kelly(analyzer)
    except Exception as e:
        logger.error(f"Kelly Criterion 分析失敗：{e}")
        results['kelly_criterion'] = {'error': str(e)}
    
    try:
        results['tilt_behavior'] = analyze_tilt(analyzer)
    except Exception as e:
        logger.error(f"傾斜行為檢測失敗：{e}")
        results['tilt_behavior'] = {'error': str(e)}
    
    try:
        results['risk_of_ruin'] = analyze_ror(analyzer)
    except Exception as e:
        logger.error(f"破產風險分析失敗：{e}")
        results['risk_of_ruin'] = {'error': str(e)}
    
    try:
        results['fee_pressure'] = analyze_fee(analyzer)
    except Exception as e:
        logger.error(f"手續費壓力分析失敗：{e}")
        results['fee_pressure'] = {'error': str(e)}
    
    try:
        results['recovery_factor'] = analyze_recovery(analyzer)
    except Exception as e:
        logger.error(f"恢復係數分析失敗：{e}")
        results['recovery_factor'] = {'error': str(e)}
    
    try:
        results['emotional_control'] = analyze_emotional(analyzer)
    except Exception as e:
        logger.error(f"情緒控制分析失敗：{e}")
        results['emotional_control'] = {'error': str(e)}
    
    try:
        results['skill_dimensions'] = analyze_skill(analyzer)
    except Exception as e:
        logger.error(f"能力評分分析失敗：{e}")
        results['skill_dimensions'] = {'error': str(e)}
    
    try:
        results['max_losing_streak'] = analyze_streak(analyzer)
    except Exception as e:
        logger.error(f"最長連損分析失敗：{e}")
        results['max_losing_streak'] = {'error': str(e)}
    
    try:
        results['short_term_trades'] = analyze_short(analyzer, short_minutes)
    except Exception as e:
        logger.error(f"短線交易分析失敗：{e}")
        results['short_term_trades'] = {'error': str(e)}
    
    try:
        results['cooling_period'] = analyze_cooling(analyzer)
    except Exception as e:
        logger.error(f"冷靜期分析失敗：{e}")
        results['cooling_period'] = {'error': str(e)}
    
    return results


def format_text_output(results: Dict[str, Any], analysis_type: str) -> str:
    """
    格式化文本輸出
    
    Args:
        results: 分析結果
        analysis_type: 分析類型
    
    Returns:
        str: 格式化的文本
    """
    lines = []
    lines.append("=" * 80)
    lines.append("量化風險分析報告")
    lines.append("=" * 80)
    lines.append(f"\n分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"分析類型: {ANALYSIS_TYPES.get(analysis_type, analysis_type)}")
    lines.append("")
    
    if analysis_type == 'all':
        # 顯示所有分析結果
        for key, data in results.items():
            if 'error' in data:
                lines.append(f"\n{'-' * 80}")
                lines.append(f"{key.upper()} - 分析失敗")
                lines.append(f"{'-' * 80}")
                lines.append(f"錯誤: {data['error']}")
                continue
            
            lines.append(f"\n{'-' * 80}")
            lines.append(f"{key.upper()}")
            lines.append(f"{'-' * 80}")
            
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    lines.append(f"{k}: {json.dumps(v, ensure_ascii=False, indent=2)}")
                elif isinstance(v, float):
                    lines.append(f"{k}: {v:.4f}")
                else:
                    lines.append(f"{k}: {v}")
    
    else:
        # 顯示單個分析結果
        if 'error' in results:
            lines.append(f"\n分析失敗: {results['error']}")
        else:
            for k, v in results.items():
                if isinstance(v, (list, dict)):
                    lines.append(f"{k}: {json.dumps(v, ensure_ascii=False, indent=2)}")
                elif isinstance(v, float):
                    lines.append(f"{k}: {v:.4f}")
                else:
                    lines.append(f"{k}: {v}")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


def save_json_output(results: Dict[str, Any], output_path: str, metadata: Dict[str, Any]):
    """
    保存 JSON 格式輸出
    
    Args:
        results: 分析結果
        output_path: 輸出文件路徑
        metadata: 元數據
    """
    output_data = {
        'metadata': metadata,
        'results': results
    }
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"結果已保存到：{output_path}")


def run_analyze_risk(args):
    """
    執行量化風險分析命令
    
    Args:
        args: 命令行參數
    """
    logger.info("開始量化風險分析")
    
    # 載入數據
    try:
        analyzer = load_trades_data(args.data)
    except Exception as e:
        print(f"錯誤：{e}")
        return
    
    # 執行分析
    analysis_type = args.analysis
    results = None
    
    try:
        if analysis_type == 'all':
            results = analyze_all(analyzer, args.short_minutes)
        elif analysis_type == 'kelly':
            results = analyze_kelly(analyzer)
        elif analysis_type == 'tilt':
            results = analyze_tilt(analyzer)
        elif analysis_type == 'ror':
            results = analyze_ror(analyzer)
        elif analysis_type == 'fee':
            results = analyze_fee(analyzer)
        elif analysis_type == 'recovery':
            results = analyze_recovery(analyzer)
        elif analysis_type == 'emotional':
            results = analyze_emotional(analyzer)
        elif analysis_type == 'skill':
            results = analyze_skill(analyzer)
        elif analysis_type == 'streak':
            results = analyze_streak(analyzer)
        elif analysis_type == 'short':
            results = analyze_short(analyzer, args.short_minutes)
        elif analysis_type == 'cooling':
            results = analyze_cooling(analyzer)
        else:
            print(f"錯誤：無效的分析類型：{analysis_type}")
            print(f"可用類型：{', '.join(ANALYSIS_TYPES.keys())}")
            return
    
    except Exception as e:
        print(f"分析失敗：{e}")
        logger.error(f"分析失敗：{e}", exc_info=True)
        return
    
    # 輸出結果
    metadata = {
        'data_file': args.data,
        'analysis_time': datetime.now().isoformat(),
        'analysis_type': analysis_type,
        'short_minutes': args.short_minutes if analysis_type in ['all', 'short'] else None,
    }
    
    if args.format == 'json' or args.output:
        # JSON 格式
        if args.output:
            save_json_output(results, args.output, metadata)
        else:
            output_data = {
                'metadata': metadata,
                'results': results
            }
            print(json.dumps(output_data, indent=2, ensure_ascii=False, default=str))
    
    else:
        # 文本格式
        text_output = format_text_output(results, analysis_type)
        print(text_output)
    
    logger.info("量化風險分析完成")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='量化風險分析 CLI 工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 顯示所有分析
  python -m cli_commands.analyze_risk --data trades.csv
  
  # 只顯示 Kelly Criterion
  python -m cli_commands.analyze_risk --data trades.csv --analysis kelly
  
  # 分析短線交易（10分鐘）
  python -m cli_commands.analyze_risk --data trades.csv --analysis short --short-minutes 10
  
  # 輸出到 JSON 文件
  python -m cli_commands.analyze_risk --data trades.csv --output result.json
        """
    )
    
    # 必需參數
    parser.add_argument(
        '--data',
        required=True,
        help='交易數據文件路徑（CSV 格式）'
    )
    
    # 可選參數
    parser.add_argument(
        '--analysis',
        default='all',
        choices=list(ANALYSIS_TYPES.keys()),
        help=f'分析類型（默認：all）'
    )
    
    parser.add_argument(
        '--short-minutes',
        type=float,
        default=5.0,
        help='短線交易時間閾值（分鐘），默認：5.0'
    )
    
    parser.add_argument(
        '--output',
        help='輸出結果到文件（JSON 格式）'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='輸出格式（默認：text）'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='顯示詳細信息'
    )
    
    args = parser.parse_args()
    
    # 設置日誌級別
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 執行命令
    run_analyze_risk(args)


if __name__ == '__main__':
    main()
