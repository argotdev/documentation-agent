import os
from typing import List, Dict, Tuple
from pathlib import Path
import anthropic
from git import Repo
from datetime import datetime, timedelta

class DocHelperAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)
        self.repo = Repo('.')
        self.changed_files = self._get_changed_files()
        self.commit_history = {}
        self._analyze_commit_history()

    def _analyze_commit_history(self, days: int = 30):
        """Analyze commit history to understand file importance."""
        since = datetime.now() - timedelta(days=days)
        commits = list(self.repo.iter_commits(since=since))
        
        for commit in commits:
            for file in commit.stats.files:
                if file.endswith('.py'):
                    self.commit_history[file] = self.commit_history.get(file, 0) + 1

    def _get_file_importance_score(self, file_path: str) -> float:
        """Calculate importance score for a file based on various factors."""
        score = 0.0
        
        # Factor 1: Recent commit frequency (0-5 points)
        commit_count = self.commit_history.get(file_path, 0)
        score += min(commit_count / 2, 5)  # Cap at 5 points
        
        # Factor 2: File size and complexity (0-3 points)
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            score += min(len(lines) / 100, 3)  # Larger files score higher, cap at 3
        
        # Factor 3: Import statements (0-2 points)
        import_count = sum(1 for line in lines if line.strip().startswith('import') or line.strip().startswith('from'))
        score += min(import_count / 5, 2)  # More imports suggest more complexity
        
        return score

    def analyze_code_importance(self, code: str) -> Dict[str, float]:
        """Have Claude analyze code importance based on various factors."""
        prompt = f"""Analyze this Python code and score each function based on these factors:
1. Complexity (0-5): Number of operations, loops, conditions
2. Impact (0-5): How much other code depends on this function
3. Clarity Need (0-5): How much documentation would help understanding

Return scores in this format:
FUNCTION: name
COMPLEXITY: score
IMPACT: score
CLARITY: score

Code to analyze:

{code}"""

        message = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        scores = {}
        current_func = None
        current_scores = {}

        for line in message.content.split('\n'):
            if line.startswith('FUNCTION:'):
                if current_func:
                    scores[current_func] = sum(current_scores.values()) / 15  # Normalize to 0-1
                current_func = line.replace('FUNCTION:', '').strip()
                current_scores = {}
            elif line.startswith(('COMPLEXITY:', 'IMPACT:', 'CLARITY:')):
                key, value = line.split(':')
                current_scores[key.lower()] = float(value.strip())

        if current_func:
            scores[current_func] = sum(current_scores.values()) / 15

        return scores

    def make_documentation_decisions(self, file_path: str, code: str) -> List[Dict]:
        """Decide which functions need documentation and in what order."""
        # Get file-level importance
        file_importance = self._get_file_importance_score(file_path)
        
        # Get function-level importance
        function_scores = self.analyze_code_importance(code)
        
        # Combine scores and make decisions
        decisions = []
        for func_name, func_score in function_scores.items():
            combined_score = (file_importance + func_score * 10) / 2
            
            if combined_score >= 3.5:  # High priority
                priority = "high"
                doc_style = "comprehensive"
            elif combined_score >= 2:  # Medium priority
                priority = "medium"
                doc_style = "standard"
            else:  # Low priority
                priority = "low"
                doc_style = "basic"
                
            decisions.append({
                "function": func_name,
                "priority": priority,
                "doc_style": doc_style,
                "score": combined_score
            })
        
        # Sort by score
        decisions.sort(key=lambda x: x['score'], reverse=True)
        return decisions

    def analyze_and_update_file(self, file_path: str) -> None:
        """Analyze file and make documentation decisions."""
        with open(file_path, 'r') as file:
            content = file.read()

        # Make decisions about what to document
        decisions = self.make_documentation_decisions(file_path, content)
        
        # Only proceed with high and medium priority functions
        functions_to_document = [d for d in decisions if d['priority'] in ['high', 'medium']]
        
        if not functions_to_document:
            print(f"No high/medium priority documentation needed for {file_path}")
            return

        # Generate documentation based on decisions
        prompt = (
            f"""For the following Python code, generate documentation for these functions:
{', '.join(d['function'] for d in functions_to_document)}

For each function, provide:
1. The function name
2. Line number where documentation should be inserted
3. A {' and '.join(f"{d['doc_style']}" for d in functions_to_document)} Google-style docstring

Return in this format:
FUNCTION: function_name
LINE: line_number
DOCSTRING:
'''your docstring here'''

Here's the code:

{content}"""
        )

        message = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        updates = self._parse_claude_response(message.content)
        if updates:
            self._apply_updates(file_path, updates)

    # ... (rest of the class methods remain the same)