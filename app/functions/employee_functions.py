async def get_karyawan(departemen: str = "semua") -> dict:
    """Get employee names by department in Indonesian"""
    karyawan = {
        "IT": ["Budi Santoso", "Dewi Putri"],
        "HR": ["Ahmad Wijaya", "Siti Rahma"],
        "Finance": ["Rini Kusuma", "Hadi Prakoso"],
    }
    return karyawan[departemen] if departemen in karyawan else karyawan
