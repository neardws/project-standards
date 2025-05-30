import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
import re

class AcademicPaperDatabase:
    def __init__(self):
        self.papers = {}
        self.authors = {}
        self.venues = {}  # 期刊和会议的统一存储
        
    def _generate_id(self) -> str:
        """生成唯一ID"""
        return str(uuid.uuid4())
    
    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email:
            return True  # 允许空邮箱
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def _validate_date(self, date_str: str) -> bool:
        """验证日期格式"""
        if not date_str:
            return False
        
        date_patterns = [
            r'^\d{4}/\d{1,2}/\d{1,2}$',  # YYYY/M/D
            r'^\d{4}-\d{1,2}-\d{1,2}$',  # YYYY-M-D
            r'^\d{4}$',  # 只有年份
        ]
        
        return any(re.match(pattern, date_str.strip()) for pattern in date_patterns)
    
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
    
    def _extract_year_from_date(self, date_str: str) -> Optional[str]:
        """从日期字符串中提取年份"""
        if not date_str:
            return None
        return date_str[:4] if len(date_str) >= 4 else None
    
    def _parse_name(self, full_name: str) -> Tuple[str, str]:
        """解析姓名为名和姓"""
        if not full_name:
            return "n/a", "n/a"
        
        name_parts = full_name.strip().split()
        if len(name_parts) == 1:
            # 只有一个名字，假设为姓
            return "n/a", name_parts[0]
        elif len(name_parts) == 2:
            # 假设第一个是名，第二个是姓
            return name_parts[0], name_parts[1]
        else:
            # 多个名字，第一个为名，其余为姓
            return name_parts[0], " ".join(name_parts[1:])
    
    def _normalize_conference_name(self, conference_name: str) -> str:
        """标准化会议名称，去除年份和届数"""
        if not conference_name:
            return conference_name
        
        # 去除年份信息 (4位数字)
        conference_name = re.sub(r'\b\d{4}\b', '', conference_name)
        
        # 去除届数信息 (如 25th, 1st, 2nd, 3rd, 11th等)
        conference_name = re.sub(r'\b\d+(st|nd|rd|th)\b', '', conference_name)
        
        # 去除多余的空格
        conference_name = re.sub(r'\s+', ' ', conference_name).strip()
        
        return conference_name
    
    def _parse_authors(self, authors_str: str) -> tuple[List[str], List[str]]:
        """解析作者字符串，返回(作者ID列表, 通讯作者ID列表)"""
        if not authors_str:
            return [], []
        
        authors = []
        corresponding_authors = []
        author_names = [name.strip() for name in authors_str.split(',')]
        
        for name in author_names:
            # 检查是否是通讯作者
            is_corresponding = '*' in name
            # 移除作者名字中的特殊标记
            clean_name = re.sub(r'[*†‡§¶]', '', name).strip()
            
            if clean_name:
                author_id = self._get_or_create_author_by_name(clean_name)
                authors.append(author_id)
                if is_corresponding:
                    corresponding_authors.append(author_id)
        
        return authors, corresponding_authors
    
    def _get_or_create_author_by_name(self, name: str) -> str:
        """仅通过姓名获取或创建作者（临时方法）"""
        first_name, last_name = self._parse_name(name)
        return self._get_or_create_author(first_name, last_name)
    
    def _author_similarity_score(self, author1: Dict, first_name: str, last_name: str, 
                               affiliation: str = None, email: str = None) -> float:
        """计算作者相似度分数"""
        score = 0.0
        
        # 姓名匹配 (权重: 0.5)
        if (author1.get('first_name', '').lower() == (first_name or '').lower() and 
            author1.get('last_name', '').lower() == (last_name or '').lower()):
            score += 0.5
        
        # 单位匹配 (权重: 0.3)
        if affiliation and author1.get('affiliation') and author1.get('affiliation') != 'n/a':
            if affiliation.lower() == author1['affiliation'].lower():
                score += 0.3
            elif affiliation.lower() in author1['affiliation'].lower() or \
                 author1['affiliation'].lower() in affiliation.lower():
                score += 0.15  # 部分匹配
        
        # 邮箱匹配 (权重: 0.2)
        if email and author1.get('email') and author1.get('email') != 'n/a':
            if email.lower() == author1['email'].lower():
                score += 0.2
        
        return score
    
    def _get_or_create_author(self, first_name: str, last_name: str, 
                            affiliation: str = None, email: str = None) -> str:
        """获取或创建作者，返回作者ID"""
        # 检查是否已存在相似的作者 (相似度阈值: 0.7)
        best_match_id = None
        best_score = 0.0
        
        for author_id, author_info in self.authors.items():
            score = self._author_similarity_score(author_info, first_name, last_name, 
                                                affiliation, email)
            if score > best_score and score >= 0.7:
                best_match_id = author_id
                best_score = score
        
        if best_match_id:
            # 更新作者信息（如果提供了新信息）
            if affiliation and self.authors[best_match_id].get('affiliation') == 'n/a':
                self.authors[best_match_id]['affiliation'] = affiliation
            if email and self.authors[best_match_id].get('email') == 'n/a':
                self.authors[best_match_id]['email'] = email
            return best_match_id
        
        # 创建新作者
        author_id = self._generate_id()
        self.authors[author_id] = {
            'id': author_id,
            'first_name': first_name or 'n/a',
            'last_name': last_name or 'n/a',
            'full_name': f"{first_name} {last_name}".strip() if first_name and last_name else 'n/a',
            'affiliation': affiliation or 'n/a',
            'email': email or 'n/a',
            'papers': [],
            'total_citations': 0
        }
        
        return author_id
    
    def _get_or_create_venue(self, venue_name: str, venue_type: str, publisher: str = None,
                           cas_division: str = None, jcr_division: str = None, 
                           ccf_class: str = None) -> str:
        """获取或创建期刊/会议，返回期刊/会议ID"""
        
        # 对会议名称进行标准化处理
        if venue_type == 'conference':
            normalized_name = self._normalize_conference_name(venue_name)
        else:
            normalized_name = venue_name
        
        # 检查是否已存在该期刊/会议
        for venue_id, venue_info in self.venues.items():
            # 安全地获取存储的名称
            if venue_type == 'conference':
                stored_name = venue_info.get('normalized_name', venue_info.get('name', ''))
            else:
                stored_name = venue_info.get('name', '')
                
            if stored_name.lower() == normalized_name.lower():
                # 更新分类信息（如果提供了新信息）
                if cas_division and venue_info.get('cas_division') == 'n/a':
                    self.venues[venue_id]['cas_division'] = cas_division
                if jcr_division and venue_info.get('jcr_division') == 'n/a':
                    self.venues[venue_id]['jcr_division'] = jcr_division
                if ccf_class and venue_info.get('ccf_class') == 'n/a':
                    self.venues[venue_id]['ccf_class'] = ccf_class
                    
                # 为旧的会议记录添加 normalized_name 字段
                if venue_type == 'conference' and 'normalized_name' not in venue_info:
                    self.venues[venue_id]['normalized_name'] = normalized_name
                    
                return venue_id
        
        # 创建新期刊/会议
        venue_id = self._generate_id()
        venue_record = {
            'id': venue_id,
            'name': venue_name,
            'type': venue_type,  # 'journal' 或 'conference'
            'publisher': publisher or 'n/a',
            'papers': [],
            'total_citations': 0
        }
        
        # 添加会议特有字段
        if venue_type == 'conference':
            venue_record['normalized_name'] = normalized_name
            venue_record['ccf_class'] = ccf_class or 'n/a'
        
        # 添加期刊特有字段
        if venue_type == 'journal':
            venue_record['cas_division'] = cas_division or 'n/a'  # 中科院分区
            venue_record['jcr_division'] = jcr_division or 'n/a'  # JCR分区
            venue_record['ccf_class'] = ccf_class or 'n/a'       # CCF分类
        
        self.venues[venue_id] = venue_record
        return venue_id
    
    def _extract_citations(self, citation_str: str) -> int:
        """从引用字符串中提取数字"""
        if not citation_str:
            return 0
        
        # 提取数字
        match = re.search(r'(\d+)', citation_str)
        return int(match.group(1)) if match else 0
    
    def add_paper(self, 
                  title: str,
                  authors: str,
                  publication_date: str,
                  paper_type: str,
                  venue_name: str = None,
                  volume: str = None,
                  issue: str = None,
                  pages: str = None,
                  publisher: str = None,
                  abstract: str = None,
                  total_citations: str = None,
                  author_affiliations: List[str] = None,
                  author_emails: List[str] = None,
                  cas_division: str = None,
                  jcr_division: str = None,
                  ccf_class: str = None) -> str:
        """
        添加论文到数据库
        
        Args:
            title: 论文标题
            authors: 作者字符串，用逗号分隔，通讯作者用*标记
            publication_date: 发表日期 (YYYY/MM/DD, YYYY-MM-DD, 或 YYYY)
            paper_type: 论文类型 ('journal' 或 'conference')
            venue_name: 期刊名或会议名
            volume: 卷号（期刊专用）
            issue: 期号（期刊专用）
            pages: 页码
            publisher: 出版社
            abstract: 摘要
            total_citations: 引用数字符串
            author_affiliations: 作者单位列表（按作者顺序）
            author_emails: 作者邮箱列表（按作者顺序）
            cas_division: 中科院分区（期刊用）
            jcr_division: JCR分区（期刊用）
            ccf_class: CCF分类（期刊和会议通用）
            
        Returns:
            str: 论文ID
            
        Raises:
            ValueError: 输入格式错误时抛出异常
        """
        
        # 输入验证
        if not title or not title.strip():
            raise ValueError("论文标题不能为空")
        
        if not authors or not authors.strip():
            raise ValueError("作者信息不能为空")
        
        if not publication_date or not self._validate_date(publication_date):
            raise ValueError("发表日期格式不正确，应为 YYYY/MM/DD、YYYY-MM-DD 或 YYYY")
        
        if paper_type not in ['journal', 'conference']:
            raise ValueError("论文类型必须是 'journal' 或 'conference'")
        
        if not venue_name or not venue_name.strip():
            raise ValueError("期刊名或会议名不能为空")
        
        # 验证邮箱格式
        if author_emails:
            for email in author_emails:
                if email and not self._validate_email(email):
                    raise ValueError(f"邮箱格式不正确: {email}")
        
        # 解析作者
        author_ids, corresponding_author_ids = self._parse_authors(authors)
        
        # 更新作者信息（单位和邮箱）
        if author_affiliations or author_emails:
            affiliations = author_affiliations or []
            emails = author_emails or []
            
            # 重新解析作者名字并更新信息
            author_names = [re.sub(r'[*†‡§¶]', '', name).strip() 
                          for name in authors.split(',')]
            
            for i, (author_id, full_name) in enumerate(zip(author_ids, author_names)):
                affiliation = affiliations[i] if i < len(affiliations) else None
                email = emails[i] if i < len(emails) else None
                
                if author_id in self.authors:
                    if affiliation and self.authors[author_id].get('affiliation') == 'n/a':
                        self.authors[author_id]['affiliation'] = affiliation
                    if email and self.authors[author_id].get('email') == 'n/a':
                        self.authors[author_id]['email'] = email
        
        # 处理期刊/会议
        venue_id = self._get_or_create_venue(venue_name, paper_type, publisher,
                                           cas_division, jcr_division, ccf_class)
        
        # 处理引用数
        citation_count = self._extract_citations(total_citations or '0')
        
        # 生成论文ID
        paper_id = self._generate_id()
        
        # 解析发表日期
        parsed_date = self._parse_date(publication_date)
        publication_year = self._extract_year_from_date(parsed_date)
        
        # 创建论文记录
        paper_record = {
            'id': paper_id,
            'title': title.strip(),
            'type': paper_type,
            'authors': author_ids,
            'corresponding_authors': corresponding_author_ids,  # 通讯作者与论文绑定
            'publication_date': parsed_date,
            'publication_year': publication_year,  # 为会议论文添加年份信息
            'venue_id': venue_id,
            'volume': volume.strip() if volume else None,
            'issue': issue.strip() if issue else None,
            'pages': pages.strip() if pages else 'n/a',
            'publisher': publisher.strip() if publisher else 'n/a',
            'abstract': (abstract[:1000] + '...') if abstract and len(abstract) > 1000 else (abstract or 'n/a'),
            'total_citations': citation_count,
            'created_at': datetime.now().isoformat()
        }
        
        # 存储论文
        self.papers[paper_id] = paper_record
        
        # 更新作者的论文列表和引用数
        for author_id in author_ids:
            if author_id in self.authors:
                self.authors[author_id]['papers'].append(paper_id)
                self.authors[author_id]['total_citations'] += citation_count
        
        # 更新期刊/会议的论文列表和引用数
        if venue_id and venue_id in self.venues:
            self.venues[venue_id]['papers'].append(paper_id)
            self.venues[venue_id]['total_citations'] += citation_count
        
        return paper_id
    
    def add_author(self, first_name: str, last_name: str, 
                   affiliation: str = None, email: str = None) -> str:
        """
        单独添加作者信息
        
        Args:
            first_name: 作者名
            last_name: 作者姓
            affiliation: 作者单位
            email: 作者邮箱
            
        Returns:
            str: 作者ID
            
        Raises:
            ValueError: 输入格式错误时抛出异常
        """
        if not first_name and not last_name:
            raise ValueError("作者姓名不能全部为空")
        
        if email and not self._validate_email(email):
            raise ValueError(f"邮箱格式不正确: {email}")
        
        return self._get_or_create_author(first_name, last_name, affiliation, email)
    
    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """获取论文信息"""
        return self.papers.get(paper_id)
    
    def get_author(self, author_id: str) -> Optional[Dict]:
        """获取作者信息"""
        return self.authors.get(author_id)
    
    def get_venue(self, venue_id: str) -> Optional[Dict]:
        """获取期刊/会议信息"""
        return self.venues.get(venue_id)
    
    def get_paper_with_details(self, paper_id: str) -> Optional[Dict]:
        """获取论文详细信息，包括作者和期刊/会议的完整信息"""
        paper = self.get_paper(paper_id)
        if not paper:
            return None
        
        # 获取作者详细信息
        authors_details = []
        for author_id in paper.get('authors', []):
            author = self.get_author(author_id)
            if author:
                authors_details.append({
                    'id': author_id,
                    'first_name': author.get('first_name', 'n/a'),
                    'last_name': author.get('last_name', 'n/a'),
                    'full_name': author.get('full_name', 'n/a'),
                    'affiliation': author.get('affiliation', 'n/a'),
                    'email': author.get('email', 'n/a'),
                    'is_corresponding': author_id in paper.get('corresponding_authors', [])
                })
        
        # 获取期刊/会议详细信息
        venue_details = None
        if paper.get('venue_id'):
            venue = self.get_venue(paper['venue_id'])
            if venue:
                venue_details = {
                    'id': venue.get('id'),
                    'name': venue.get('name', 'n/a'),
                    'type': venue.get('type', 'n/a'),
                    'publisher': venue.get('publisher', 'n/a')
                }
                
                # 添加分类信息
                if venue.get('type') == 'journal':
                    venue_details.update({
                        'cas_division': venue.get('cas_division', 'n/a'),
                        'jcr_division': venue.get('jcr_division', 'n/a'),
                        'ccf_class': venue.get('ccf_class', 'n/a')
                    })
                elif venue.get('type') == 'conference':
                    venue_details.update({
                        'normalized_name': venue.get('normalized_name', 'n/a'),
                        'ccf_class': venue.get('ccf_class', 'n/a')
                    })
        
        return {
            **paper,
            'authors_details': authors_details,
            'venue_details': venue_details
        }
    
    def search_papers(self, **kwargs) -> List[Dict]:
        """搜索论文"""
        results = []
        for paper in self.papers.values():
            match = True
            
            # 按标题搜索
            if 'title' in kwargs:
                if kwargs['title'].lower() not in paper.get('title', '').lower():
                    match = False
            
            # 按类型搜索
            if 'type' in kwargs:
                if paper.get('type') != kwargs['type']:
                    match = False
            
            # 按年份搜索
            if 'year' in kwargs:
                if paper.get('publication_year'):
                    if paper['publication_year'] != str(kwargs['year']):
                        match = False
                else:
                    match = False
            
            # 按作者搜索
            if 'author' in kwargs:
                author_found = False
                for author_id in paper.get('authors', []):
                    author = self.get_author(author_id)
                    if author and (kwargs['author'].lower() in author.get('full_name', '').lower() or
                                 kwargs['author'].lower() in author.get('first_name', '').lower() or
                                 kwargs['author'].lower() in author.get('last_name', '').lower()):
                        author_found = True
                        break
                if not author_found:
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
    
    try:
        # 示例1：期刊论文
        paper1_id = db.add_paper(
            title='A Hierarchical Architecture for the Future Internet of Vehicles',
            authors='Kai Liu*, Xincao Xu, Mengliang Chen, Bingyi Liu*, Libing Wu, Victor CS Lee',
            publication_date='2019/7/19',
            paper_type='journal',
            venue_name='IEEE Communications Magazine',
            volume='57',
            issue='7',
            pages='41-47',
            publisher='IEEE',
            abstract='Recent advances in wireless communication, sensing, computation and control technologies have paved the way for the development of a new era of Internet of Vehicles (IoV)...',
            total_citations='Cited by 138',
            author_affiliations=[
                'Beijing University of Technology',
                'Beijing University of Technology', 
                'Beijing University of Technology',
                'Beijing University of Technology',
                'Beijing University of Technology',
                'The Chinese University of Hong Kong'
            ],
            author_emails=[
                'kailiu@bjut.edu.cn',
                'xuxincao@bjut.edu.cn',
                'chenmengliang@bjut.edu.cn',
                'liubingyi@bjut.edu.cn',
                'wulibing@bjut.edu.cn',
                'victor@cuhk.edu.hk'
            ],
            cas_division='二区',
            jcr_division='Q1',
            ccf_class='B'
        )
        
        # 示例2：会议论文
        paper2_id = db.add_paper(
            title='Age of View: A New Metric for Evaluating Heterogeneous Information Fusion in Vehicular Cyber-Physical Systems',
            authors='Xincao Xu, Kai Liu*, Qisen Zhang, Hao Jiang, Ke Xiao, Jiangtao Luo',
            publication_date='2022/10/8',
            paper_type='conference',
            venue_name='2022 IEEE 25th International Conference on Intelligent Transportation Systems (ITSC)',
            pages='3762-3767',
            publisher='IEEE',
            abstract='Heterogeneous information fusion is one of the most critical issues for realizing vehicular cyber-physical systems (VCPSs)...',
            total_citations='Cited by 8',
            ccf_class='C'
        )
        
        print(f"成功添加期刊论文，ID: {paper1_id}")
        print(f"成功添加会议论文，ID: {paper2_id}")
        
        # 获取论文详细信息
        paper_details = db.get_paper_with_details(paper1_id)
        print(f"\n论文详细信息:")
        print(f"标题: {paper_details['title']}")
        print(f"作者:")
        for author in paper_details['authors_details']:
            corresponding = " (通讯作者)" if author['is_corresponding'] else ""
            print(f"  - {author['full_name']}{corresponding}")
            print(f"    名: {author['first_name']}, 姓: {author['last_name']}")
            print(f"    单位: {author['affiliation']}")
            print(f"    邮箱: {author['email']}")
        
        print(f"\n期刊信息:")
        venue = paper_details['venue_details']
        print(f"  期刊名: {venue['name']}")
        print(f"  出版社: {venue['publisher']}")
        print(f"  中科院分区: {venue['cas_division']}")
        print(f"  JCR分区: {venue['jcr_division']}")
        print(f"  CCF分类: {venue['ccf_class']}")
        
        # 查看会议论文详情
        paper2_details = db.get_paper_with_details(paper2_id)
        print(f"\n会议论文详细信息:")
        print(f"标题: {paper2_details['title']}")
        print(f"发表年份: {paper2_details['publication_year']}")
        venue2 = paper2_details['venue_details']
        print(f"会议原名: {venue2['name']}")
        print(f"会议标准名: {venue2['normalized_name']}")
        print(f"CCF分类: {venue2['ccf_class']}")
        
        # 导出数据
        db.export_to_json('academic_papers.json')
        print("\n数据已导出到 academic_papers.json")
        
        # 搜索示例
        papers_2019 = db.search_papers(year=2019)
        print(f"\n2019年的论文数量: {len(papers_2019)}")
        
        journal_papers = db.search_papers(type='journal')
        print(f"期刊论文数量: {len(journal_papers)}")
        
        liu_papers = db.search_papers(author='Kai Liu')
        print(f"Kai Liu的论文数量: {len(liu_papers)}")
        
    except ValueError as e:
        print(f"输入错误: {e}")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    main()
