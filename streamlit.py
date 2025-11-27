# ============================================================
# QUIKKO - FULL APP (Login + Register + Forgot Password + Orders)
# (Order History Removed from UI)
# ============================================================

import streamlit as st
import pandas as pd
import uuid
import hashlib
from snowflake.snowpark.context import get_active_session


st.set_page_config(page_title="Quikko App", layout="wide")

# -------------------------- PASSWORD HASHER -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ====================================================================
#  LOGIN / REGISTER / FORGOT PASSWORD SCREENS
# ====================================================================

def show_login_screen():
    st.title("🔐 Quikko Login")
    tab_login, tab_register = st.tabs(["🔑 Login", "🧍 Register"])

    # ---------------------- LOGIN TAB ----------------------
    with tab_login:
        with st.form("login_form"):
            identifier = st.text_input("Email or Phone")
            password = st.text_input("Password", type="password")
            login_click = st.form_submit_button("🚀 Login")

        if login_click:
            hashed = hash_password(password)

            df = session.sql(f"""
                SELECT * FROM QUIKKO_DB.USERS.USERS 
                WHERE (EMAIL='{identifier}' OR PHONE='{identifier}')
                  AND PASSWORD_HASH='{hashed}'
            """).to_pandas()

            if not df.empty:
                st.session_state["user_logged_in"] = True
                st.session_state["user_info"] = df.iloc[0].to_dict()
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid login credentials")

        st.write("---")

        if st.button("🔄 Forgot Password?"):
            st.session_state["reset_password_mode"] = True
            st.rerun()

    # ---------------------- REGISTER TAB ----------------------
    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            user_type = st.selectbox("User Type", ["CUSTOMER", "VENDOR", "ADMIN"])
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            reg_submit = st.form_submit_button("📝 Register")

        if reg_submit:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                hashed = hash_password(password)

                exists = session.sql(f"""
                    SELECT * FROM QUIKKO_DB.USERS.USERS WHERE EMAIL='{email}'
                """).to_pandas()

                if not exists.empty:
                    st.warning("Email already registered!")
                else:
                    user_id = f"U_{uuid.uuid4().hex[:6].upper()}"

                    session.sql(f"""
                        INSERT INTO QUIKKO_DB.USERS.USERS
                        (USER_ID, FULL_NAME, EMAIL, PHONE, USER_TYPE, PASSWORD_HASH)
                        VALUES (
                            '{user_id}', '{full_name}', '{email}', 
                            '{phone}', '{user_type}', '{hashed}'
                        )
                    """).collect()

                    st.success("🎉 Registration successful! You may login now.")
                    st.balloons()


# ====================================================================
#  RESET PASSWORD SCREEN
# ====================================================================

def show_reset_password_screen():
    st.title("🔄 Reset Password")

    with st.form("reset_form"):
        email = st.text_input("Enter your registered Email")
        new_pass = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("✔ Reset Password")

    if submit:
        if new_pass != confirm:
            st.error("Passwords do not match.")
        else:
            hashed = hash_password(new_pass)

            session.sql(f"""
                UPDATE QUIKKO_DB.USERS.USERS
                SET PASSWORD_HASH='{hashed}'
                WHERE EMAIL='{email}'
            """).collect()

            st.success("Password updated successfully!")
            st.session_state["reset_password_mode"] = False
            st.rerun()


# ====================================================================
# MAIN APPLICATION (AFTER LOGIN)
# ====================================================================

def show_main_app():
    st.title("🛒 Quikko Order Management (Dynamic + Payments)")

    user = st.session_state["user_info"]

    # SIDEBAR
    st.sidebar.header("👤 Profile")
    st.sidebar.write(f"**Name:** {user['FULL_NAME']}")
    st.sidebar.write(f"**Email:** {user['EMAIL']}")
    st.sidebar.write(f"**Phone:** {user['PHONE']}")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    # =======================================
    # PRODUCT LIST
    # =======================================

    products = {
        "Veg Biryani": 120, "Paneer Biryani": 150, "Veg Meals": 100,
        "Idly (2pcs)": 40, "Dosa": 60, "Masala Dosa": 80, "Poori": 70, "Chapathi": 50,
        "Chicken Biryani": 180, "Mutton Biryani": 250, "Egg Biryani": 140,
        "Chicken Fry": 160, "Chicken Curry": 150, "Fish Fry": 200, "Prawns Curry": 220
    }

    st.subheader("🆕 Place Order")

    with st.form("order_form", clear_on_submit=True):
        selected_items = st.multiselect(
            "Select Items", [f"{k} – ₹{v}" for k, v in products.items()]
        )

        address_id = st.text_input("Address ID", value="ADDR1001")

        total_amount = 0
        order_items = {}

        if selected_items:
            st.write("### Items & Qty")
            for item in selected_items:
                name = item.split(" – ")[0]
                price = products[name]
                qty = st.number_input(f"{name} Qty", min_value=1, value=1, key=f"qty_{name}")
                order_items[name] = qty
                total_amount += qty * price

            st.info(f"### 💰 Total Amount: ₹{total_amount}")

        place = st.form_submit_button("📦 Place Order")

    if place:
        order_id = f"ORD_{uuid.uuid4().hex[:6].upper()}"
        session.sql(f"""
            INSERT INTO QUIKKO_DB.ORDERS.ORDERS
            (ORDER_ID, USER_ID, ADDRESS_ID, TOTAL_AMOUNT, STATUS, ORDER_DATE)
            VALUES ('{order_id}','{user['USER_ID']}','{address_id}',
                    {total_amount},'PENDING', CURRENT_TIMESTAMP())
        """).collect()

        for name, qty in order_items.items():
            item_id = f"IT_{uuid.uuid4().hex[:6].upper()}"
            price = products[name]

            session.sql(f"""
                INSERT INTO QUIKKO_DB.ORDERS.ORDER_ITEMS
                (ORDER_ITEM_ID, ORDER_ID, PRODUCT_ID, QUANTITY, PRICE)
                VALUES ('{item_id}','{order_id}','{name}',{qty},{price})
            """).collect()

        st.success(f"Order {order_id} placed!")
        st.rerun()

    # =======================================
    # YOUR ACTIVE ORDERS
    # =======================================

    st.subheader("📋 Your Active Orders")

    orders = session.sql(f"""
        SELECT ORDER_ID, USER_ID, ADDRESS_ID, ORDER_DATE, STATUS,
               TOTAL_AMOUNT, IS_CANCELLED, CANCEL_REASON, UPDATED_AT
        FROM QUIKKO_DB.ORDERS.ORDERS
        WHERE USER_ID='{user['USER_ID']}'
        ORDER BY ORDER_DATE DESC
    """).to_pandas()

    # ---------------- CANCEL LOGIC ----------------

    if st.session_state.get("cancel_order_id"):
        cancel_id = st.session_state["cancel_order_id"]

        st.warning(f"Cancel Order: {cancel_id}")

        reason = st.selectbox(
            "Reason",
            ["Changed my mind", "Ordered by mistake", "Found better price", "Other"],
            key=f"reason_{cancel_id}"
        )

        other = ""
        if reason == "Other":
            other = st.text_input("Enter custom reason", key=f"other_{cancel_id}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Confirm Cancel", key=f"confirm_{cancel_id}"):
                final_reason = other if reason == "Other" else reason

                session.sql(f"""
                    UPDATE QUIKKO_DB.ORDERS.ORDERS
                    SET IS_CANCELLED=1,
                        CANCEL_REASON='{final_reason}',
                        UPDATED_AT=CURRENT_TIMESTAMP()
                    WHERE ORDER_ID='{cancel_id}'
                """).collect()

                st.success("Order cancelled.")
                st.session_state["cancel_order_id"] = None
                st.rerun()

        with col2:
            if st.button("Dismiss", key=f"dismiss_{cancel_id}"):
                st.session_state["cancel_order_id"] = None
                st.rerun()

    # ---------------- SHOW ACTIVE ORDERS ----------------

    if not orders.empty:
        for _, row in orders.iterrows():
            col1, col2 = st.columns([8, 1])

            with col1:
                st.table(pd.DataFrame([row]))

            with col2:
                if row["IS_CANCELLED"] != 1:
                    oid = row["ORDER_ID"]
                    if st.button("Cancel Order", key=f"cancel_btn_{oid}"):
                        st.session_state["cancel_order_id"] = oid
                        st.rerun()
                else:
                    st.write("Cancelled")
    else:
        st.info("No active orders.")

    # =======================================
    # PAYMENT (ARCHIVE COMPLETED ORDERS)
    # =======================================

    st.subheader("💳 Payments")

    pending = orders[(orders["IS_CANCELLED"] != 1)]
    pending = pending[pending["STATUS"] != "COMPLETED"]

    if not pending.empty:
        order_id = st.selectbox("Select Order to Pay", pending["ORDER_ID"])
        amount = pending[pending["ORDER_ID"] == order_id]["TOTAL_AMOUNT"].iloc[0]

        method = st.selectbox("Payment Method", ["UPI", "Card", "Wallet"])

        if st.button("Pay Now"):
            pay_id = f"PAY_{uuid.uuid4().hex[:6].upper()}"
            txn = f"TXN_{uuid.uuid4().hex[:6].upper()}"
            hist_id = f"HIST_{uuid.uuid4().hex[:6].upper()}"

            # 1️⃣ Payment record
            session.sql(f"""
                INSERT INTO QUIKKO_DB.ORDERS.PAYMENTS
                (PAYMENT_ID, ORDER_ID, USER_ID, PAYMENT_METHOD,
                 TRANSACTION_ID, AMOUNT, PAYMENT_STATUS, PAYMENT_DATE)
                VALUES ('{pay_id}','{order_id}','{user['USER_ID']}',
                        '{method}','{txn}',{amount},'SUCCESS', CURRENT_TIMESTAMP())
            """).collect()

            # 2️⃣ Mark COMPLETED
            session.sql(f"""
                UPDATE QUIKKO_DB.ORDERS.ORDERS
                SET STATUS='COMPLETED', UPDATED_AT=CURRENT_TIMESTAMP()
                WHERE ORDER_ID='{order_id}'
            """).collect()

            # 3️⃣ Archive full row
            session.sql(f"""
                INSERT INTO QUIKKO_DB.ORDERS.ORDER_HISTORY
                (HISTORY_ID, ORDER_ID, USER_ID, ADDRESS_ID, ORDER_DATE,
                 STATUS, TOTAL_AMOUNT, IS_CANCELLED, CANCEL_REASON,
                 COMMENT, UPDATED_BY, UPDATED_AT, CHANGED_AT)
                SELECT
                    '{hist_id}',
                    ORDER_ID, USER_ID, ADDRESS_ID, ORDER_DATE,
                    'COMPLETED',
                    TOTAL_AMOUNT, IS_CANCELLED, CANCEL_REASON,
                    'Order paid and archived',
                    '{user['FULL_NAME']}',
                    UPDATED_AT,
                    CURRENT_TIMESTAMP()
                FROM QUIKKO_DB.ORDERS.ORDERS
                WHERE ORDER_ID='{order_id}'
            """).collect()

            # 4️⃣ Remove from active orders
            session.sql(f"""
                DELETE FROM QUIKKO_DB.ORDERS.ORDERS
                WHERE ORDER_ID='{order_id}'
            """).collect()

            st.success(f"Payment completed. Order {order_id} archived.")
            st.balloons()
            st.rerun()

    else:
        st.info("No orders pending for payment.")


# ====================================================================
# ROUTING
# ====================================================================

if st.session_state.get("reset_password_mode"):
    show_reset_password_screen()
elif not st.session_state.get("user_logged_in"):
    show_login_screen()
else:
    show_main_app()
