"""Sprint 5.5: 轻量级 RAG 检索增强

设计目标：
  - 首次启动从 metrics_dict.json + glossary.json 灌入知识库
  - 提供关键词检索 + 简单向量相似度检索（TF-IDF 风格，无需外部依赖）
  - 召回 Top-K 文档拼接到 LLM Prompt 中，提升专业问题准确率

依赖说明：
  - 默认采用 TF-IDF 余弦相似度算法，零额外依赖
  - 可选安装 sentence-transformers / chromadb 切换为向量检索
"""

import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

# 知识库存储目录
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
METRICS_PATH = KNOWLEDGE_DIR.parent / "core" / "metrics_dict.json"
GLOSSARY_PATH = KNOWLEDGE_DIR / "glossary.json"


def _tokenize(text: str) -> List[str]:
    """中文友好的分词：按字符 unigram + 关键词 bigram"""
    text = re.sub(r"[^\w\u4e00-\u9fa5]+", " ", text.lower())
    tokens = list(text)
    # 加入二元组提升中文匹配精度
    bigrams = [text[i:i+2] for i in range(len(text)-1) if len(text[i:i+2].strip()) == 2]
    return tokens + bigrams


def _tfidf_score(query_tokens: List[str], doc_tokens: List[str], idf: Dict[str, float]) -> float:
    """计算 TF-IDF 余弦相似度"""
    if not doc_tokens or not query_tokens:
        return 0.0
    q_counter = Counter(query_tokens)
    d_counter = Counter(doc_tokens)

    score = 0.0
    for token, q_tf in q_counter.items():
        if token in d_counter:
            d_tf = d_counter[token]
            score += (q_tf * idf.get(token, 1.0)) * (d_tf * idf.get(token, 1.0))
    # 归一化
    q_norm = math.sqrt(sum((q_tf * idf.get(t, 1.0))**2 for t, q_tf in q_counter.items()))
    d_norm = math.sqrt(sum((d_tf * idf.get(t, 1.0))**2 for t, d_tf in d_counter.items()))
    if q_norm == 0 or d_norm == 0:
        return 0.0
    return score / (q_norm * d_norm)


class RagRetriever:
    """轻量级 RAG 检索器（零外部依赖）"""

    def __init__(self):
        self.docs: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.idf: Dict[str, float] = {}
        self._indexed = False
        self._ingest()

    def _ingest(self):
        """首次启动灌入：指标口径 + 业务术语"""
        all_docs = []

        # 1. 灌入指标口径（来自 metrics_dict.json）
        if METRICS_PATH.exists():
            try:
                metrics_raw = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
                for m in metrics_raw.get("metrics", []):
                    doc_text = (
                        f"指标：{m.get('metric_name', '')}（{m.get('metric_id', '')}）"
                        f"业务域：{m.get('business_domain', '')}"
                        f"定义：{m.get('definition', '')}"
                        f"计算规则：{m.get('calculation_rule', '')}"
                        f"示例SQL：{m.get('example_query', '')}"
                    )
                    all_docs.append({
                        "id": f"metric_{m.get('metric_id', '')}",
                        "type": "metric",
                        "title": m.get("metric_name", ""),
                        "domain": m.get("business_domain", ""),
                        "content": doc_text,
                        "raw": m
                    })
            except Exception as e:
                print(f"⚠️ 指标字典加载失败: {e}")

        # 2. 灌入业务术语（来自 glossary.json）
        if GLOSSARY_PATH.exists():
            try:
                glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
                for term in glossary.get("terms", []):
                    synonyms = "、".join(term.get("synonyms", []))
                    doc_text = (
                        f"术语：{term.get('name', '')}"
                        f"别名：{synonyms}"
                        f"定义：{term.get('definition', '')}"
                    )
                    all_docs.append({
                        "id": f"term_{term.get('name', '')}",
                        "type": "glossary",
                        "title": term.get("name", ""),
                        "domain": "业务术语",
                        "content": doc_text,
                        "raw": term
                    })
            except Exception as e:
                print(f"⚠️ 术语表加载失败: {e}")

        self.docs = all_docs
        self.doc_tokens = [_tokenize(d["content"]) for d in all_docs]

        # 计算 IDF
        df: Counter = Counter()
        for tokens in self.doc_tokens:
            for token in set(tokens):
                df[token] += 1
        N = len(self.doc_tokens) or 1
        self.idf = {token: math.log(N / (1 + freq)) + 1 for token, freq in df.items()}

        self._indexed = True
        print(f"📚 RAG 知识库灌库完成：{len(self.docs)} 条文档（{len([d for d in self.docs if d['type']=='metric'])} 指标 + {len([d for d in self.docs if d['type']=='glossary'])} 术语）")

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.05) -> List[Dict[str, Any]]:
        """
        检索与查询最相关的 Top-K 文档

        Args:
            query: 用户自然语言查询
            top_k: 返回前 K 条
            min_score: 最低相似度阈值，低于此分视为不相关

        Returns:
            包含 doc / score / meta 的检索结果列表
        """
        if not self._indexed or not self.docs:
            return []

        query_tokens = _tokenize(query)
        scored = []
        for i, doc_tokens in enumerate(self.doc_tokens):
            score = _tfidf_score(query_tokens, doc_tokens, self.idf)
            if score >= min_score:
                scored.append((score, i))

        scored.sort(reverse=True, key=lambda x: x[0])
        top = scored[:top_k]

        results = []
        for score, idx in top:
            doc = self.docs[idx]
            results.append({
                "doc": doc["content"],
                "title": doc.get("title", ""),
                "type": doc.get("type", ""),
                "domain": doc.get("domain", ""),
                "score": round(score, 4),
                "raw": doc.get("raw", {})
            })
        return results

    def build_context_block(self, query: str, top_k: int = 3) -> str:
        """将检索结果格式化为可注入 Prompt 的字符串"""
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return ""
        lines = ["【RAG 知识库检索结果（Top-{}）】".format(len(results))]
        for i, r in enumerate(results, 1):
            lines.append(f"\n[{i}] {r['title']}（{r['type']}/{r['domain']}，相关度 {r['score']}）")
            lines.append(f"    {r['doc']}")
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "total_docs": len(self.docs),
            "metric_count": len([d for d in self.docs if d["type"] == "metric"]),
            "glossary_count": len([d for d in self.docs if d["type"] == "glossary"]),
            "vocab_size": len(self.idf),
            "indexed": self._indexed
        }


# 单例
_rag_instance: Optional[RagRetriever] = None


def get_rag() -> RagRetriever:
    """获取 RAG 检索器单例"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagRetriever()
    return _rag_instance


def quick_test():
    """快速自检"""
    rag = get_rag()
    print("\n" + json.dumps(rag.stats(), ensure_ascii=False, indent=2))
    print("\n--- 测试 query: '埃安3月达成率' ---")
    for r in rag.retrieve("埃安3月达成率", top_k=3):
        print(f"  [{r['score']:.3f}] {r['title']} ({r['type']})")
    print("\n--- 测试 query: '什么是 CPL' ---")
    for r in rag.retrieve("什么是 CPL", top_k=2):
        print(f"  [{r['score']:.3f}] {r['title']} ({r['type']})")


if __name__ == "__main__":
    quick_test()
