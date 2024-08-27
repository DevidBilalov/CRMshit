import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError
from models import Customer, engine

with engine.connect() as connection:
    result = connection.execute(text("PRAGMA table_info(customers)"))
    columns = [row[1] for row in result]

    if 'created_at' not in columns:
        connection.execute(text("ALTER TABLE customers ADD COLUMN created_at TIMESTAMP"))

Session = scoped_session(sessionmaker(bind=engine))

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///customers.db')
}

executors = {
    'default': ThreadPoolExecutor(10)
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, timezone='UTC')
scheduler.start()

class CRMApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CRM")
        self.geometry("480x480")

        self.name_label = tk.Label(self, text="Name:")
        self.name_label.pack()
        self.name_entry = tk.Entry(self)
        self.name_entry.pack()

        self.email_label = tk.Label(self, text="Email:")
        self.email_label.pack()
        self.email_entry = tk.Entry(self)
        self.email_entry.pack()

        self.phone_label = tk.Label(self, text="Phone:")
        self.phone_label.pack()
        self.phone_entry = tk.Entry(self)
        self.phone_entry.pack()

        self.date_label = tk.Label(self, text="Reminder Date (DD-MM-YYYY HH:MM):")
        self.date_label.pack()
        self.date_entry = tk.Entry(self)
        self.date_entry.pack()

        self.info_label = tk.Label(self, text="Info (optional):")
        self.info_label.pack()
        self.info_entry = tk.Entry(self)
        self.info_entry.pack()

        self.add_button = tk.Button(self, text="Add", command=self.add_customer)
        self.add_button.pack()

        self.update_button = tk.Button(self, text="Update Info", command=self.update_info)
        self.update_button.pack()

        self.list_button = tk.Button(self, text="List", command=self.list_customers)
        self.list_button.pack()

        self.search_date_button = tk.Button(self, text="Search by Date", command=self.search_by_date)
        self.search_date_button.pack()

        self.search_phone_button = tk.Button(self, text="Search", command=self.search_by_phone)
        self.search_phone_button.pack()

        self.delete_button = tk.Button(self, text="Delete", command=self.delete_customer)
        self.delete_button.pack()

    def add_customer(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        date_str = self.date_entry.get().strip()
        info = self.info_entry.get().strip()
        if name and email and phone and date_str:
            try:
                reminder_time = datetime.strptime(date_str, '%d-%m-%Y %H:%M')

                existing_customer = Session.query(Customer).filter_by(phone=phone).first()
                if existing_customer:
                    messagebox.showerror("Error", f"Customer with phone {phone} already exists.")
                    return
                new_customer = Customer(name=name, email=email, phone=phone, info=info)
                Session.add(new_customer)
                Session.commit()

                job_id = f'admin_reminder_{new_customer.id}'

                scheduler.add_job(
                    self.send_admin_reminder,
                    'date',
                    run_date=reminder_time,
                    args=[new_customer.id],
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=604800
                 )
                return

                
                messagebox.showinfo("Success", "Customer added and reminder set.")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use DD-MM-YYYY HH:MM.")
            except IntegrityError:
                Session.rollback()
                messagebox.showerror("Error", f"Customer with phone {phone} already exists.")
            except Exception as ex:
                Session.rollback()
                messagebox.showerror("Error", f"Error: {ex}")
            finally:
                Session.remove()
        else:
            messagebox.showerror("Error", "Please fill in all fields.")

    def list_customers(self):
        try:
            customers = Session.query(Customer).all()
            if customers:
                customer_list = '\n'.join([f'{customer.id}. {customer.name} - {customer.phone} - {customer.email}' for customer in customers])
                messagebox.showinfo("Customer List", customer_list)
            else:
                messagebox.showinfo("Customer List", "No customers found.")
        finally:
            Session.remove()

    def delete_customer(self):
        phone = self.phone_entry.get().strip()

        try:
            customer = Session.query(Customer).filter_by(phone=phone).first()
            if customer:
                try:
                    job_id = f'admin_reminder_{customer.id}'
                except JobLookupError:
                    pass

                Session.delete(customer)
                Session.commit()
                messagebox.showinfo("Success", f"Customer {customer.name} deleted.")
            else:
                messagebox.showerror("Error", "Customer not found.")
        finally:
            Session.remove()

    def search_by_date(self):
        date_str = self.date_entry.get().strip()
        try:
            search_date = datetime.strptime(date_str, '%d-%m-%Y')
            customers = Session.query(Customer).filter(
                Customer.created_at >= search_date,
                Customer.created_at < search_date + timedelta(days=1)
            ).all()

            if customers:
                customer_list = '\n'.join([f'{customer.id}. {customer.name} - {customer.phone} - {customer.email} - {customer.info}' for customer in customers])
                messagebox.showinfo("Search Results", customer_list)
            else:
                messagebox.showinfo("Search Results", "No customers found on this date.")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use DD-MM-YYYY.")
        finally:
            Session.remove()

    def update_info(self):
        phone = self.phone_entry.get().strip()
        new_info = self.info_entry.get().strip()

        try:
            customer = Session.query(Customer).filter_by(phone=phone).first()
            if customer:
                customer.info = new_info 
                Session.commit()
                messagebox.showinfo("Success", f"Info updated for {customer.name}.")
            else:
                messagebox.showerror("Error", "Customer not found.")
        finally:
            Session.remove()

    def search_by_phone(self):
        phone = self.phone_entry.get().strip()
        try:
            customer = Session.query(Customer).filter_by(phone=phone).first()

            if customer:
                customer_info = f'{customer.id}. {customer.name} - {customer.phone} - {customer.email} - {customer.info}'
                messagebox.showinfo("Search Results", customer_info)
            else:
                messagebox.showinfo("Search Results", "No customer found with this phone number.")
        finally:
            Session.remove()

    def send_admin_reminder(self, customer_id):
        pirnt(13)
        try:
            print(1)
            customer = Session.query(Customer).get(customer_id)
            messagebox.showinfo("Reminder", f"Reminder: Call {customer.name} ({customer.phone})")
            print(2)
        finally:
            Session.remove()

        

if __name__ == "__main__":
    app = CRMApp()
    app.mainloop()
    