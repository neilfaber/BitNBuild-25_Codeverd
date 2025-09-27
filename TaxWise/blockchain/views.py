from django.shortcuts import render, redirect
from django.http import JsonResponse
from .contract import w3, contract, account  # account is LocalAccount

def add_record_form(request):
    if request.method == "POST":
        taxpayer = request.POST.get("taxpayer")
        amount = request.POST.get("amount")

        if taxpayer and amount:
            try:
                # Use account.address for the sender
                tx_hash = contract.functions.addRecord(taxpayer, amount).transact({
                    "from": account.address
                })
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                return render(request, "blockchain/add_record.html", {
                    "status": "success",
                    "txHash": tx_hash.hex(),
                    "taxpayer": taxpayer,
                    "amount": amount
                })

            except Exception as e:
                return render(request, "blockchain/add_record.html", {
                    "status": "error",
                    "message": f"Transaction failed: {str(e)}"
                })

        else:
            return render(request, "blockchain/add_record.html", {
                "status": "error",
                "message": "Both taxpayer and amount fields are required."
            })

    return render(request, "blockchain/add_record.html")


def get_record_form(request):
    record_data = None
    if request.method == "POST":
        try:
            record_id = int(request.POST.get("record_id"))
            record = contract.functions.getRecord(record_id).call()
            record_data = {
                "taxpayer": record[0],
                "amount": record[1],
                "timestamp": record[2],
            }
        except Exception as e:
            return render(request, "blockchain/get_record.html", {
                "status": "error",
                "message": f"Failed to fetch record: {str(e)}"
            })

    return render(request, "blockchain/get_record.html", {"record": record_data})
