from utils.file_handler import save_file

def process_files(files: list):
    saved_files = []
    errors = []
    for file_data in files:
        try:
            saved_files.append(save_file(file_data))
        except Exception as e:
            errors.append({"file_name": file_data.get("name"), "error": str(e)})
    return saved_files, errors