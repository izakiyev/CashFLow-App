import os
import csv

def export_csv(filepath, data, headers):
    """
    Exports a list of dictionaries to a CSV file.
    """
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return filepath
    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return None

def export_excel(filepath, data, headers):
    """
    Exports data to Excel using openpyxl.
    """
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Export"

        for col_idx, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_idx, value=header)

        for row_idx, row_data in enumerate(data, 2):
            for col_idx, key in enumerate(headers, 1):
                ws.cell(row=row_idx, column=col_idx, value=row_data.get(key, ""))

        wb.save(filepath)
        return filepath
    except ImportError:
        print("openpyxl is not installed.")
        return None
    except Exception as e:
        print(f"Error exporting Excel: {e}")
        return None

def export_pdf(filepath, title, data, headers):
    """
    Exports data to a basic PDF using reportlab.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(title, styles['Title']))

        table_data = [headers]
        for row in data:
            table_data.append([str(row.get(h, "")) for h in headers])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(t)
        doc.build(elements)
        return filepath
    except ImportError:
        print("reportlab is not installed.")
        return None
    except Exception as e:
        print(f"Error exporting PDF: {e}")
        return None

def export_all_json(filepath, company_id):
    """
    Exports all company data (accounts, transactions, categories, planned payments) to a JSON file.
    """
    import json
    from database.session import get_session
    from database.models import Account, Transaction, Category, PlannedPayment

    def dt(d):
        return d.isoformat() if d else None

    with get_session() as session:
        accounts = [
            {"id": a.id, "name": a.name, "type": a.type, "currency": a.currency,
             "balance": float(a.balance), "color": a.color}
            for a in session.query(Account).filter_by(company_id=company_id).all()
        ]
        transactions = [
            {"id": t.id, "account_id": t.account_id, "type": t.type, "amount": float(t.amount),
             "currency": t.currency, "description": t.description, "category_id": t.category_id,
             "date": dt(t.date), "to_account_id": t.to_account_id}
            for t in session.query(Transaction).filter_by(company_id=company_id).all()
        ]
        categories = [
            {"id": c.id, "name": c.name, "type": c.type, "color": c.color}
            for c in session.query(Category).filter_by(company_id=company_id).all()
        ]
        planned = [
            {"id": p.id, "account_id": p.account_id, "type": p.type, "amount": float(p.amount),
             "description": p.description, "due_date": dt(p.due_date),
             "status": p.status, "recurring": p.recurring}
            for p in session.query(PlannedPayment).filter_by(company_id=company_id).all()
        ]

        payload = {
            "company_id": company_id,
            "accounts": accounts,
            "transactions": transactions,
            "categories": categories,
            "planned_payments": planned,
        }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return filepath

def clear_all_data(company_id):
    """
    Deletes all transactions, planned payments, categories, and accounts for a company.
    Leaves the company and user records intact.
    """
    from database.session import get_session
    from database.models import Account, Transaction, Category, PlannedPayment

    with get_session() as session:
        session.query(Transaction).filter_by(company_id=company_id).delete()
        session.query(PlannedPayment).filter_by(company_id=company_id).delete()
        session.query(Category).filter_by(company_id=company_id).delete()
        session.query(Account).filter_by(company_id=company_id).delete()
        session.commit()
