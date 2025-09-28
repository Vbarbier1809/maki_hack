#!/usr/bin/env python3
"""
Script to automatically update assistantService.ts with real answers from completed_questions JSON
"""

import json
import os
import re
import glob
from typing import Dict, List

class AssistantAnswerUpdater:
    def __init__(self):
        self.assistant_service_path = "../assistantService.ts"
        self.completed_questions_pattern = "completed_questions_*.json"
    
    def find_latest_completed_questions_file(self) -> str:
        """Find the most recent completed_questions JSON file"""
        files = glob.glob(self.completed_questions_pattern)
        if not files:
            raise FileNotFoundError("No completed_questions_*.json files found")
        
        # Sort by modification time, get the most recent
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    
    def load_completed_questions(self, file_path: str) -> Dict:
        """Load completed questions data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            raise
    
    def extract_real_answers(self, completed_data: Dict) -> Dict[str, str]:
        """Extract real answers from completed questions data"""
        real_answers = {}
        
        for question in completed_data.get('questions', []):
            question_id = str(question.get('id'))
            responses = question.get('responses', [])
            
            if responses:
                # Use the first response as the answer
                real_answers[question_id] = responses[0]
        
        return real_answers
    
    def map_answers_to_types(self, real_answers: Dict[str, str]) -> Dict[str, str]:
        """Map real answers to question types based on your data structure"""
        # Based on your questions.json structure:
        # 1: "What sports do you like?" -> text
        # 2: "Tell me about your education background" -> textarea/long_text  
        # 3: "What age do you like?" -> number
        # 4: "Give me your email" -> email
        # 5: "Are you at Dauphine University?" -> boolean/radio/choice
        # 6: "tell me anything you want" -> default
        
        type_mapping = {
            'text': real_answers.get('1', 'I really like football.'),
            'textarea': real_answers.get('2', 'So I\'ve done ESAP, an engineering school based in Paris, and then I\'ve done Dauphine, University Dauphine.'),
            'long_text': real_answers.get('2', 'So I\'ve done ESAP, an engineering school based in Paris, and then I\'ve done Dauphine, University Dauphine.'),
            'number': real_answers.get('3', 'I really like the age 42'),
            'email': real_answers.get('4', 'My email address is Victor.Santiller at gmail.com'),
            'radio': real_answers.get('5', 'Yes, I am. Yes, indeed.'),
            'choice': real_answers.get('5', 'Yes, I am. Yes, indeed.'),
            'boolean': real_answers.get('5', 'Yes, I am. Yes, indeed.'),
            'default': real_answers.get('6', 'Yeah, I like the hackathon right now, take AI with Maki people, it\'s really nice.')
        }
        
        return type_mapping
    
    def generate_switch_case_code(self, type_answers: Dict[str, str]) -> str:
        """Generate the switch case code with real answers"""
        # Escape single quotes for JavaScript
        def escape_js_string(s):
            return s.replace("'", "\\'").replace('"', '\\"')
        
        code = """        questions.questions.forEach((question) => {
          switch (question.type_answer.toLowerCase()) {
            case 'text':
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['text']) + """';
              break;
            case 'textarea':
            case 'long_text':
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['textarea']) + """';
              break;
            case 'number':
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['number']) + """';
              break;
            case 'email':
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['email']) + """';
              break;
            case 'radio':
            case 'choice':
            case 'boolean':
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['boolean']) + """';
              break;
            case 'checkbox':
              dummyAnswers[question.question_id] = true;
              break;
            default:
              dummyAnswers[question.question_id] = '""" + escape_js_string(type_answers['default']) + """';
          }
        });"""
        
        return code
    
    def update_assistant_service(self) -> bool:
        """Update the assistantService.ts file with real answers"""
        try:
            print("🔄 Updating assistantService.ts with latest answers...")
            
            # Find the latest completed questions file
            latest_file = self.find_latest_completed_questions_file()
            print(f"📁 Using data from: {latest_file}")
            
            # Load and extract answers
            completed_data = self.load_completed_questions(latest_file)
            real_answers = self.extract_real_answers(completed_data)
            
            if not real_answers:
                print("⚠️  No real answers found in completed questions file")
                return False
            
            print(f"📊 Found {len(real_answers)} real answers:")
            for qid, answer in real_answers.items():
                truncated = answer[:50] + "..." if len(answer) > 50 else answer
                print(f"   Q{qid}: \"{truncated}\"")
            
            # Map answers to question types
            type_answers = self.map_answers_to_types(real_answers)
            
            # Read current assistant service file
            if not os.path.exists(self.assistant_service_path):
                print(f"❌ Assistant service file not found: {self.assistant_service_path}")
                return False
            
            with open(self.assistant_service_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate new switch case code
            new_code = self.generate_switch_case_code(type_answers)
            
            # Replace the forEach loop with new code
            pattern = r'questions\.questions\.forEach\(\(question\)\s*=>\s*\{[\s\S]*?\}\);'
            
            if not re.search(pattern, content):
                print("❌ Could not find the questions.forEach loop in assistantService.ts")
                return False
            
            updated_content = re.sub(pattern, new_code, content)
            
            # Write updated content back
            with open(self.assistant_service_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ Successfully updated assistantService.ts with real answers!")
            return True
            
        except Exception as e:
            print(f"❌ Error updating assistant service: {e}")
            return False

def main():
    """Main function for CLI usage"""
    updater = AssistantAnswerUpdater()
    success = updater.update_assistant_service()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
