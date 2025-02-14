async def get_menu(category: str = "all") -> dict:
    menu = {
        "appetizers": ["Spring Rolls", "Salad"],
        "main": ["Noodles", "Rice"],
        "desserts": ["Ice Cream"]
    }
    return menu[category] if category in menu else menu
