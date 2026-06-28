from decimal import Decimal, InvalidOperation


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _same_amount(left, right):
    return left == right


def process_transactions(
    parsed_data,
    normal_fee,
    discounted_fee,
    fetch_ecp,
    fetch_member_by_id,
    empty_label="N/A",
    invalid_amount_label="Invalid amount in transaction",
):
    normal_fee = Decimal(str(normal_fee))
    discounted_fee = Decimal(str(discounted_fee))
    processed_transactions = []

    for tx_data in parsed_data.get("transactions", []):
        ecp_hash = tx_data.get("ecp_hash_candidate")
        tx_amount = _to_decimal(tx_data.get("amount", 0))
        processed_tx = {
            "ecp_hash_display": ecp_hash or empty_label,
            "name_or_iban": "",
            "amount": tx_amount if tx_amount is not None else Decimal("0"),
            "currency": tx_data.get("currency", ""),
            "payment_date": tx_data.get("transaction_date", empty_label),
            "bg_color": "white",
            "text_color": "black",
            "status": "unprocessed",
        }

        if tx_amount is None:
            processed_tx["bg_color"] = "lightgray"
            processed_tx["name_or_iban"] = invalid_amount_label
            processed_tx["status"] = "invalid_amount"
            processed_transactions.append(processed_tx)
            continue

        member = None
        ecp_record = None
        if ecp_hash:
            ecp_record = fetch_ecp(ecp_hash)
            if ecp_record:
                member = fetch_member_by_id(ecp_record.member_id)

        if member and ecp_record:
            processed_tx["name_or_iban"] = f"{member.first_name} {member.last_name}"
            expected_fee = discounted_fee if member.discounted_membership else normal_fee

            if ecp_record.is_ecp_active:
                if _same_amount(tx_amount, expected_fee):
                    processed_tx["bg_color"] = "lightgreen"
                    processed_tx["status"] = "valid"
                elif tx_amount < expected_fee:
                    processed_tx["bg_color"] = "salmon"
                    processed_tx["status"] = "underpaid"
                else:
                    processed_tx["bg_color"] = "lightblue"
                    processed_tx["status"] = "overpaid"
            elif _same_amount(tx_amount, normal_fee) or _same_amount(tx_amount, discounted_fee):
                processed_tx["bg_color"] = "yellow"
                processed_tx["status"] = "inactive_expected_amount"
            else:
                processed_tx["bg_color"] = "lightgray"
                processed_tx["status"] = "inactive_wrong_amount"
        else:
            processed_tx["bg_color"] = "lightgray"
            processed_tx["name_or_iban"] = tx_data.get("debtor_account_iban", empty_label)
            if _same_amount(tx_amount, normal_fee) or _same_amount(tx_amount, discounted_fee):
                processed_tx["text_color"] = "darkGreen"
                processed_tx["status"] = "unknown_reference_expected_amount"
            else:
                processed_tx["text_color"] = "red"
                processed_tx["status"] = "unknown_reference_wrong_amount"

        processed_transactions.append(processed_tx)

    return processed_transactions
