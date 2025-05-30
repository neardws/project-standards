import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union
import re

class AcademicPaperDatabase:
    def __init__(self):
        self.papers = {}
        self.authors = {}
        self.venues = {}  # 期刊和会议的统一存储
        
    def _generate_id(self) -> str:
        """生成唯一ID"""
        return str(uuid.uuid4())
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串，返回标准格式"""
        if not date_str:
            return None
        
        # 尝试解析不同的日期格式
        date_patterns = [
            r'(\d{4})/(\d{1,2})/(\d{1,2})',  # YYYY/M/D
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-M-D
            r'(\d{4})',  # 只有年份
        ]
        
        for pattern in date_patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                if len(match.groups()) == 1:  # 只有年份
                    return f"{match.group(1)}-01-01"
                else:
                    year, month, day = match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return date_str  # 如果无法解析，返回原字符串
    
    def _parse_authors(self, authors_str: str) -> List[str]:
        """解析作者字符串，返回作者ID列表"""
        if not authors_str:
            return []
        
        # 按逗号分割作者，处理特殊标记如*
        authors = []
        author_names = [name.strip() for name in authors_str.split(',')]
        
        for name in author_names:
            # 移除作者名字中的特殊标记（如*表示通讯作者）
            clean_name = re.sub(r'[*†‡§¶]', '', name).strip()
            if clean_name:
                author_id = self._get_or_create_author(clean_name, '*' in name)
                authors.append(author_id)
        
        return authors
    
    def _get_or_create_author(self, name: str, is_corresponding: bool = False) -> str:
        """获取或创建作者，返回作者ID"""
        # 检查是否已存在该作者
        for author_id, author_info in self.authors.items():
            if author_info['name'].lower() == name.lower():
                return author_id
        
        # 创建新作者
        author_id = self._generate_id()
        self.authors[author_id] = {
            'id': author_id,
            'name': name,
            'is_corresponding': is_corresponding,
            'papers': [],
            'total_citations': 0
        }
        
        return author_id
    
    def _get_or_create_venue(self, venue_name: str, venue_type: str, publisher: str = None) -> str:
        """获取或创建期刊/会议，返回期刊/会议ID"""
        # 检查是否已存在该期刊/会议
        for venue_id, venue_info in self.venues.items():
            if venue_info['name'].lower() == venue_name.lower():
                return venue_id
        
        # 创建新期刊/会议
        venue_id = self._generate_id()
        self.venues[venue_id] = {
            'id': venue_id,
            'name': venue_name,
            'type': venue_type,  # 'journal' 或 'conference'
            'publisher': publisher or 'n/a',
            'papers': [],
            'total_citations': 0
        }
        
        return venue_id
    
    def _extract_citations(self, citation_str: str) -> int:
        """从引用字符串中提取数字"""
        if not citation_str:
            return 0
        
        # 提取数字
        match = re.search(r'(\d+)', citation_str)
        return int(match.group(1)) if match else 0
    
    def _validate_paper_data(self, paper_data: Dict) -> Dict:
        """验证和标准化论文数据"""
        validated_data = {}
        
        # 必填字段
        validated_data['title'] = paper_data.get('title', 'n/a')
        validated_data['type'] = paper_data.get('type', 'n/a')  # 'journal' 或 'conference'
        
        # 作者处理
        authors_str = paper_data.get('authors', '')
        validated_data['authors'] = self._parse_authors(authors_str)
        
        # 日期处理
        validated_data['publication_date'] = self._parse_date(paper_data.get('publication_date', ''))
        
        # 期刊/会议处理
        venue_name = paper_data.get('journal') or paper_data.get('conference', '')
        if venue_name:
            venue_type = 'journal' if paper_data.get('journal') else 'conference'
            validated_data['venue_id'] = self._get_or_create_venue(
                venue_name, venue_type, paper_data.get('publisher')
            )
        else:
            validated_data['venue_id'] = None
        
        # 期刊特有字段
        validated_data['volume'] = paper_data.get('volume') or None
        validated_data['issue'] = paper_data.get('issue') or None
        
        # 通用字段
        validated_data['pages'] = paper_data.get('pages') or 'n/a'
        validated_data['publisher'] = paper_data.get('publisher') or 'n/a'
        validated_data['abstract'] = paper_data.get('abstract', '')[:1000] + '...' if len(paper_data.get('abstract', '')) > 1000 else paper_data.get('abstract', 'n/a')
        
        # 引用数处理
        citations_str = paper_data.get('total_citations', '0')
        validated_data['total_citations'] = self._extract_citations(citations_str)
        
        return validated_data
    
    def add_paper(self, paper_data: Dict) -> str:
        """添加论文到数据库"""
        # 验证数据
        validated_data = self._validate_paper_data(paper_data)
        
        # 生成论文ID
        paper_id = self._generate_id()
        
        # 创建论文记录
        paper_record = {
            'id': paper_id,
            'title': validated_data['title'],
            'type': validated_data['type'],
            'authors': validated_data['authors'],
            'publication_date': validated_data['publication_date'],
            'venue_id': validated_data['venue_id'],
            'volume': validated_data['volume'],
            'issue': validated_data['issue'],
            'pages': validated_data['pages'],
            'publisher': validated_data['publisher'],
            'abstract': validated_data['abstract'],
            'total_citations': validated_data['total_citations'],
            'created_at': datetime.now().isoformat()
        }
        
        # 存储论文
        self.papers[paper_id] = paper_record
        
        # 更新作者的论文列表
        for author_id in validated_data['authors']:
            if author_id in self.authors:
                self.authors[author_id]['papers'].append(paper_id)
                self.authors[author_id]['total_citations'] += validated_data['total_citations']
        
        # 更新期刊/会议的论文列表
        if validated_data['venue_id'] and validated_data['venue_id'] in self.venues:
            self.venues[validated_data['venue_id']]['papers'].append(paper_id)
            self.venues[validated_data['venue_id']]['total_citations'] += validated_data['total_citations']
        
        return paper_id
    
    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """获取论文信息"""
        return self.papers.get(paper_id)
    
    def get_author(self, author_id: str) -> Optional[Dict]:
        """获取作者信息"""
        return self.authors.get(author_id)
    
    def get_venue(self, venue_id: str) -> Optional[Dict]:
        """获取期刊/会议信息"""
        return self.venues.get(venue_id)
    
    def search_papers(self, **kwargs) -> List[Dict]:
        """搜索论文"""
        results = []
        for paper in self.papers.values():
            match = True
            
            # 按标题搜索
            if 'title' in kwargs:
                if kwargs['title'].lower() not in paper['title'].lower():
                    match = False
            
            # 按类型搜索
            if 'type' in kwargs:
                if paper['type'] != kwargs['type']:
                    match = False
            
            # 按年份搜索
            if 'year' in kwargs:
                if paper['publication_date']:
                    paper_year = paper['publication_date'][:4]
                    if paper_year != str(kwargs['year']):
                        match = False
                else:
                    match = False
            
            if match:
                results.append(paper)
        
        return results
    
    def export_to_json(self, filename: str = None) -> Dict:
        """导出所有数据到JSON"""
        data = {
            'papers': self.papers,
            'authors': self.authors,
            'venues': self.venues,
            'metadata': {
                'total_papers': len(self.papers),
                'total_authors': len(self.authors),
                'total_venues': len(self.venues),
                'exported_at': datetime.now().isoformat()
            }
        }
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return data
    
    def load_from_json(self, filename: str):
        """从JSON文件加载数据"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.papers = data.get('papers', {})
        self.authors = data.get('authors', {})
        self.venues = data.get('venues', {})


# 使用示例
def main():
    # 创建数据库实例
    db = AcademicPaperDatabase()
    
    # 示例1：期刊论文
    journal_paper = {
        'title': 'A Hierarchical Architecture for the Future Internet of Vehicles',
        'type': 'journal',
        'authors': 'Kai Liu*, Xincao Xu, Mengliang Chen, Bingyi Liu*, Libing Wu, Victor CS Lee',
        'publication_date': '2019/7/19',
        'journal': 'IEEE Communications Magazine',
        'volume': '57',
        'issue': '7',
        'pages': '41-47',
        'publisher': 'IEEE',
        'abstract': 'Recent advances in wireless communication, sensing, computation and control technologies have paved the way for the development of a new era of Internet of Vehicles (IoV)...',
        'total_citations': 'Cited by 138'
    }
    
    # 示例2：会议论文
    conference_paper = {
        'title': 'Age of View: A New Metric for Evaluating Heterogeneous Information Fusion in Vehicular Cyber-Physical Systems',
        'type': 'conference',
        'authors': 'Xincao Xu, Kai Liu*, Qisen Zhang, Hao Jiang, Ke Xiao, Jiangtao Luo',
        'publication_date': '2022/10/8',
        'conference': '2022 IEEE 25th International Conference on Intelligent Transportation Systems (ITSC)',
        'pages': '3762-3767',
        'publisher': 'IEEE',
        'abstract': 'Heterogeneous information fusion is one of the most critical issues for realizing vehicular cyber-physical systems (VCPSs)...',
        'total_citations': 'Cited by 8'
    }
    
    # 添加论文
    paper1_id = db.add_paper(journal_paper)
    paper2_id = db.add_paper(conference_paper)
    
    print(f"添加期刊论文，ID: {paper1_id}")
    print(f"添加会议论文，ID: {paper2_id}")
    
    # 导出数据
    db.export_to_json('academic_papers.json')
    print("\n数据已导出到 academic_papers.json")
    
    # 搜索示例
    papers_2019 = db.search_papers(year=2019)
    print(f"\n2019年的论文数量: {len(papers_2019)}")
    
    journal_papers = db.search_papers(type='journal')
    print(f"期刊论文数量: {len(journal_papers)}")


if __name__ == "__main__":
    main()
