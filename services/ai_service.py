from google import genai
from config import SETTINGS_PATH
import json
import os
from database.session import get_session
from database.models import Transaction, Company, Category, Account, PlannedPayment
from sqlalchemy import func

class AIService:
    def __init__(self, company_id=None):
        self.company_id = company_id
        self.api_key = None
        self.ai_model = "gemini-2.5-flash"
        self._load_config()
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _load_config(self):
        if not self.company_id:
            return
        try:
            with get_session() as session:
                comp = session.get(Company, self.company_id)
                if comp:
                    self.api_key = comp.ai_api_key
                    self.ai_model = comp.ai_model or "gemini-2.5-flash"
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("AI config load failed: %s", e)

    def _get_context(self):
        if not self.company_id:
            return "No company context."
        try:
            with get_session() as session:
                comp = session.get(Company, self.company_id)
                bc = comp.currency if comp else "AZN"
                
                # 1. Accounts
                accounts = session.query(Account).filter(Account.company_id == self.company_id).all()
                acc_info = "Accounts & Balances:\n"
                for a in accounts:
                    acc_info += f"- {a.name}: {a.balance} {a.currency}\n"
                
                # 2. Recent Transactions (last 30)
                txs = (session.query(Transaction)
                       .filter(Transaction.company_id == self.company_id)
                       .order_by(Transaction.date.desc())
                       .limit(30).all())
                tx_info = "Recent Transactions:\n"
                for t in txs:
                    status_str = f" [{t.status}]" if t.status != 'paid' else ""
                    base_val = f" (≈ {t.base_amount} {bc})" if t.currency != bc and t.base_amount else ""
                    tx_info += f"- {t.date.strftime('%Y-%m-%d')}: {t.type} {t.amount} {t.currency}{base_val}{status_str} ({t.description})\n"
                
                # 3. Planned Payments
                planned = (session.query(PlannedPayment)
                           .filter(PlannedPayment.company_id == self.company_id)
                           .order_by(PlannedPayment.due_date)
                           .all())
                pl_info = "Planned Payments (Pending/Paid):\n"
                for p in planned:
                    from services.currency_service import convert_to_base
                    p_base = convert_to_base(p.amount, p.currency, bc)
                    base_val = f" (≈ {p_base} {bc})" if p.currency != bc else ""
                    pl_info += f"- {p.due_date.strftime('%Y-%m-%d')}: {p.type} {p.amount} {p.currency}{base_val} | Status: {p.status} ({p.description})\n"
                
                # 4. Categories Hierarchy
                cats = session.query(Category).filter(Category.company_id == self.company_id).all()
                cat_map = {c.id: c for c in cats}
                cat_info = "Categories (Hierarchy):\n"
                for c in cats:
                    if c.parent_id is None:
                        cat_info += f"- {c.name} ({c.type})\n"
                        children = [x for x in cats if x.parent_id == c.id]
                        for child in children:
                            cat_info += f"  └─ {child.name}\n"

                # 5. Budget Status
                from services.budget_service import get_budgets
                budgets = get_budgets(self.company_id)
                budget_info = "\nMonthly Budget Status:\n"
                for b in budgets:
                    if b['budgeted_amount'] > 0:
                        budget_info += f"- {b['category_name']}: {b['actual_amount']} / {b['budgeted_amount']} {b['currency']}\n"

                return f"Company Base Currency: {bc}\n\n{acc_info}\n{tx_info}\n{pl_info}\n{cat_info}\n{budget_info}"
        except Exception as e:
            return f"Error gathering context: {e}"

    def get_financial_insights(self, data_summary=None):
        if not self.client:
            return "Süni İntellekt deaktivdir. Zəhmət olmasa Ayarlar bölməsində Gemini API açarını əlavə edin."
        
        context = self._get_context()
        prompt = f"""
        Siz kiçik və orta biznes üçün peşəkar maliyyə məsləhətçisisiniz. 
        Aşağıdakı maliyyə məlumatlarını analiz edin və 3-4 qısa, faydalı məsləhət və ya xəbərdarlıq verin.
        Nağd pul axını (cash flow), xərcləmə modelləri və potensial risklərə diqqət yetirin.
        Mütləq Planned Payments statusuna diqqət yetirin (əgər status 'paid'dirsə, o artıq ödənilib).
        
        Cavabı mütləq AZƏRBAYCAN DİLİNDƏ (Azerbaijani language) verin.
        Professional, həvəsləndirici və qısa olun (maddələr şəklində).
        
        DİQQƏT: Əgər təqdim olunan maliyyə məlumatları boşdursa (hesablarda pul yoxdur, tranzaksiya yoxdur), heç bir uydurma rəqəm və ya ssenari yaratmayın. Sadəcə bildirin ki, sistemdə hələ məlumat yoxdur və istifadəçini ilk tranzaksiyasını əlavə etməyə həvəsləndirin.
        
        MİLLİYYƏ MƏLUMATLARI:
        {context}
        """
        if data_summary:
            prompt += f"\nƏLAVƏ XÜLASƏ:\n{data_summary}"
        try:
            response = self.client.models.generate_content(model=self.ai_model, contents=prompt)
            return response.text
        except Exception as e:
            return f"Analiz zamanı xəta baş verdi: {e}"

class AIAssistant:
    """Handles the Interactive Chat and Quick Insights for the AIAssistantPage."""
    def __init__(self, company_id):
        self.company_id = company_id
        self.service = AIService(company_id=self.company_id)
        self.history = []

    def send(self, text):
        if not self.service.client:
            return "AI is not configured. Please add an API Key in Settings."
        
        # Add context about the company
        context = self._get_context()
        prompt = f"COMPANY CONTEXT:\n{context}\n\nUSER QUESTION: {text}"
        
        try:
            response = self.service.client.models.generate_content(
                model=self.service.ai_model,
                contents=prompt
            )
            self.history.append({"role": "user", "parts": [{"text": prompt}]})
            self.history.append({"role": "model", "parts": [{"text": response.text}]})
            return response.text
        except Exception as e:
            return f"I encountered an error: {e}"

    def generate_insights(self):
        """Generates 3-4 quick insight cards for the sidebar."""
        if not self.service.client:
            return []
            
        context = self._get_context()
        prompt = f"""
        Based on this financial data:
        {context}
        
        Generate 3 concise financial insights. For each insight, provide:
        1. An emoji icon.
        2. A short title (max 5 words).
        3. A detailed description (1-2 sentences).
        4. A color category (one of: 'blue', 'green', 'red', 'orange').
        
        IMPORTANT: If the financial data is completely empty (no accounts, no transactions), do not invent any numbers. Instead, provide 3 general tips about the importance of tracking finances, budgeting, and adding the first transaction.
        
        Format your response ONLY as a JSON list of objects:
        [{{ "icon": "📈", "title": "...", "description": "...", "color": "..." }}]
        """
        try:
            response = self.service.client.models.generate_content(
                model=self.service.ai_model,
                contents=prompt
            )
            # Find the JSON part in case the model adds extra text
            text = response.text
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except:
            pass
        return [
            {"icon": "💡", "title": "Data Ready", "description": "Ask me about your top spending categories or monthly trends.", "color": "blue"}
        ]

    def _get_context(self):
        return self.service._get_context()
