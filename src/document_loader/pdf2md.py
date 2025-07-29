import os
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

def pdf_to_markdown(pdf_path: str, output_dir: str = "output") -> str:
    """
    使用minerU(magic_pdf)将PDF转为Markdown和图片，返回Markdown文件路径
    """
    name_without_suff = os.path.splitext(os.path.basename(pdf_path))[0]
    local_image_dir = os.path.join(output_dir, "images")
    local_md_dir = output_dir
    image_dir = os.path.basename(local_image_dir)
    os.makedirs(local_image_dir, exist_ok=True)
    image_writer = FileBasedDataWriter(local_image_dir)
    md_writer = FileBasedDataWriter(local_md_dir)
    # 读取PDF字节流
    reader1 = FileBasedDataReader("")
    pdf_bytes = reader1.read(pdf_path)
    # 创建数据集实例
    ds = PymuDocDataset(pdf_bytes)
    # 推理
    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(doc_analyze, ocr=True)
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    else:
        infer_result = ds.apply(doc_analyze, ocr=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)
    # 输出Markdown
    md_file = os.path.join(local_md_dir, f"{name_without_suff}.md")
    pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir)
    return md_file

def batch_pdf_to_markdown(pdf_dir: str, output_dir: str = "output") -> list:
    """
    批量将目录下所有PDF转为Markdown，返回所有Markdown文件路径
    """
    md_files = []
    for file in os.listdir(pdf_dir):
        if file.lower().endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, file)
            md_file = pdf_to_markdown(pdf_path, output_dir)
            md_files.append(md_file)
    return md_files 