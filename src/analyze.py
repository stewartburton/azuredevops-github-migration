#!/usr/bin/env python3
"""
Analysis tool for Azure DevOps organizations to help plan migrations.
"""

import json
import csv
from typing import Dict, List, Any
from datetime import datetime
try:
    from .migrate import AzureDevOpsClient
except ImportError:
    from migrate import AzureDevOpsClient
import yaml


class AzureDevOpsAnalyzer:
    """Analyzer for Azure DevOps organizations."""
    
    def __init__(self, config_file: str = "migration_config.yaml"):
        self.config = self.load_config(config_file)
        self.client = AzureDevOpsClient(
            self.config['azure_devops']['organization'],
            self.config['azure_devops']['personal_access_token']
        )
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def analyze_organization(self) -> Dict[str, Any]:
        """Analyze the entire Azure DevOps organization."""
        print("🔍 Analyzing Azure DevOps organization...")
        
        projects = self.client.get_projects()
        analysis = {
            'organization': self.config['azure_devops']['organization'],
            'analysis_date': datetime.now().isoformat(),
            'total_projects': len(projects),
            'projects': []
        }
        
        for project in projects:
            print(f"  📁 Analyzing project: {project['name']}")
            project_analysis = self.analyze_project(project)
            analysis['projects'].append(project_analysis)
        
        return analysis
    
    def analyze_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a specific project."""
        project_name = project['name']
        
        try:
            repositories = self.client.get_repositories(project_name)
            work_items = self.client.get_work_items(project_name)
            
            repo_analysis = []
            total_pull_requests = 0
            
            for repo in repositories:
                try:
                    pull_requests = self.client.get_pull_requests(project_name, repo['id'])
                    total_pull_requests += len(pull_requests)
                    
                    repo_info = {
                        'name': repo['name'],
                        'id': repo['id'],
                        'url': repo.get('webUrl', ''),
                        'size': repo.get('size', 0),
                        'default_branch': repo.get('defaultBranch', 'main'),
                        'pull_requests_count': len(pull_requests),
                        'is_empty': repo.get('size', 0) == 0
                    }
                    repo_analysis.append(repo_info)
                    
                except Exception as e:
                    print(f"    ⚠️  Could not analyze repository {repo['name']}: {str(e)}")
                    repo_analysis.append({
                        'name': repo['name'],
                        'id': repo['id'],
                        'error': str(e)
                    })
            
            # Analyze work items by type
            work_item_types = {}
            work_item_states = {}
            
            for item in work_items:
                fields = item.get('fields', {})
                item_type = fields.get('System.WorkItemType', 'Unknown')
                item_state = fields.get('System.State', 'Unknown')
                
                work_item_types[item_type] = work_item_types.get(item_type, 0) + 1
                work_item_states[item_state] = work_item_states.get(item_state, 0) + 1
            
            return {
                'name': project_name,
                'id': project['id'],
                'description': project.get('description', ''),
                'visibility': project.get('visibility', 'private'),
                'state': project.get('state', 'wellFormed'),
                'repositories_count': len(repositories),
                'repositories': repo_analysis,
                'work_items_count': len(work_items),
                'work_item_types': work_item_types,
                'work_item_states': work_item_states,
                'total_pull_requests': total_pull_requests
            }
            
        except Exception as e:
            print(f"    ❌ Error analyzing project {project_name}: {str(e)}")
            return {
                'name': project_name,
                'id': project['id'],
                'error': str(e)
            }
    
    def generate_migration_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate migration recommendations based on analysis."""
        recommendations = []
        
        for project in analysis['projects']:
            if 'error' in project:
                continue
            
            for repo in project.get('repositories', []):
                if 'error' in repo:
                    continue
                
                recommendation = {
                    'project_name': project['name'],
                    'repo_name': repo['name'],
                    'github_repo_name': repo['name'].lower().replace(' ', '-'),
                    'migrate_issues': project['work_items_count'] > 0,
                    'priority': self.calculate_migration_priority(repo, project),
                    'estimated_effort': self.estimate_migration_effort(repo, project),
                    'notes': []
                }
                
                # Add notes based on analysis
                if repo.get('is_empty'):
                    recommendation['notes'].append("Repository is empty")
                    recommendation['priority'] = 'low'
                
                if repo.get('pull_requests_count', 0) > 100:
                    recommendation['notes'].append(f"High PR activity ({repo['pull_requests_count']} PRs)")
                
                if project['work_items_count'] > 500:
                    recommendation['notes'].append(f"Large number of work items ({project['work_items_count']})")
                    recommendation['estimated_effort'] = 'high'
                
                recommendations.append(recommendation)
        
        # Sort by priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
        
        return recommendations
    
    def calculate_migration_priority(self, repo: Dict[str, Any], project: Dict[str, Any]) -> str:
        """Calculate migration priority for a repository."""
        score = 0
        
        # Size factor
        size = repo.get('size', 0)
        if size > 1000000:  # Large repo
            score += 2
        elif size > 100000:  # Medium repo
            score += 1
        
        # Activity factor
        pr_count = repo.get('pull_requests_count', 0)
        if pr_count > 50:
            score += 2
        elif pr_count > 10:
            score += 1
        
        # Work items factor
        work_items_count = project.get('work_items_count', 0)
        if work_items_count > 100:
            score += 2
        elif work_items_count > 10:
            score += 1
        
        # Empty repo penalty
        if repo.get('is_empty'):
            score -= 3
        
        if score >= 4:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def estimate_migration_effort(self, repo: Dict[str, Any], project: Dict[str, Any]) -> str:
        """Estimate migration effort."""
        effort_score = 0
        
        # Repository complexity
        if repo.get('pull_requests_count', 0) > 100:
            effort_score += 2
        elif repo.get('pull_requests_count', 0) > 20:
            effort_score += 1
        
        # Work items complexity
        work_items_count = project.get('work_items_count', 0)
        if work_items_count > 200:
            effort_score += 2
        elif work_items_count > 50:
            effort_score += 1
        
        # Repository size
        size = repo.get('size', 0)
        if size > 5000000:  # Very large
            effort_score += 2
        elif size > 1000000:  # Large
            effort_score += 1
        
        if effort_score >= 4:
            return 'high'
        elif effort_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def export_analysis_report(self, analysis: Dict[str, Any], format: str = 'json'):
        """Export analysis report in specified format."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        org_name = analysis['organization']
        
        if format.lower() == 'json':
            filename = f"analysis_report_{org_name}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
        
        elif format.lower() == 'csv':
            filename = f"analysis_report_{org_name}_{timestamp}.csv"
            self.export_csv_report(analysis, filename)
        
        print(f"📊 Analysis report exported: {filename}")
        return filename
    
    def export_csv_report(self, analysis: Dict[str, Any], filename: str):
        """Export analysis as CSV report."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'project_name', 'repo_name', 'repo_size', 'pull_requests_count',
                'work_items_count', 'is_empty', 'migration_priority', 'estimated_effort'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for project in analysis['projects']:
                if 'error' in project:
                    continue
                
                for repo in project.get('repositories', []):
                    if 'error' in repo:
                        continue
                    
                    priority = self.calculate_migration_priority(repo, project)
                    effort = self.estimate_migration_effort(repo, project)
                    
                    writer.writerow({
                        'project_name': project['name'],
                        'repo_name': repo['name'],
                        'repo_size': repo.get('size', 0),
                        'pull_requests_count': repo.get('pull_requests_count', 0),
                        'work_items_count': project.get('work_items_count', 0),
                        'is_empty': repo.get('is_empty', False),
                        'migration_priority': priority,
                        'estimated_effort': effort
                    })
    
    def create_migration_plan(self, analysis: Dict[str, Any]) -> str:
        """Create a migration plan JSON file based on analysis."""
        recommendations = self.generate_migration_recommendations(analysis)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"migration_plan_{analysis['organization']}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        print(f"📋 Migration plan created: {filename}")
        return filename


def main():
    """Main entry point for the analysis tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Azure DevOps Organization Analyzer')
    parser.add_argument('--config', default='migration_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                       help='Export format for analysis report')
    parser.add_argument('--create-plan', action='store_true',
                       help='Create migration plan based on analysis')
    parser.add_argument('--project', 
                       help='Analyze specific project only')
    
    args = parser.parse_args()
    
    try:
        analyzer = AzureDevOpsAnalyzer(args.config)
        
        if args.project:
            # Analyze specific project
            projects = analyzer.client.get_projects()
            project = next((p for p in projects if p['name'] == args.project), None)
            
            if not project:
                print(f"❌ Project '{args.project}' not found")
                exit(1)
            
            print(f"🔍 Analyzing project: {args.project}")
            project_analysis = analyzer.analyze_project(project)
            
            analysis = {
                'organization': analyzer.config['azure_devops']['organization'],
                'analysis_date': datetime.now().isoformat(),
                'total_projects': 1,
                'projects': [project_analysis]
            }
        else:
            # Analyze entire organization
            analysis = analyzer.analyze_organization()
        
        # Print summary
        print("\n📊 Analysis Summary:")
        print("=" * 50)
        print(f"Organization: {analysis['organization']}")
        print(f"Projects analyzed: {analysis['total_projects']}")
        
        total_repos = sum(len(p.get('repositories', [])) for p in analysis['projects'] if 'error' not in p)
        total_work_items = sum(p.get('work_items_count', 0) for p in analysis['projects'] if 'error' not in p)
        
        print(f"Total repositories: {total_repos}")
        print(f"Total work items: {total_work_items}")
        
        # Export report
        report_file = analyzer.export_analysis_report(analysis, args.format)
        
        # Create migration plan if requested
        if args.create_plan:
            plan_file = analyzer.create_migration_plan(analysis)
            print(f"\n💡 Next steps:")
            print(f"1. Review the migration plan: {plan_file}")
            print(f"2. Edit the plan to customize repository names and settings")
            print(f"3. Run: python batch_migrate.py --plan {plan_file}")
        
        print(f"\n✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()