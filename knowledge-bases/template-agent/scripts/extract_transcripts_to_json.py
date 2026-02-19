"""
Extract Transcripts to JSON
============================
This script reads transcript files from the knowledge base transcripts folder
and creates a structured JSON file with text, reference, and metadata.

Usage:
    python scripts/extract_transcripts_to_json.py [knowledge_base_name]

Example:
    python scripts/extract_transcripts_to_json.py nutria
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import re


def extract_metadata_from_filename(filename: str) -> dict:
    """Extract metadata from filename."""
    metadata = {
        "filename": filename,
        "title": filename.replace('.txt', ''),
        "date": None,
        "type": None
    }
    
    # Try to extract date patterns (e.g., "061025", "261025")
    date_match = re.search(r'(\d{6})', filename)
    if date_match:
        date_str = date_match.group(1)
        try:
            # Assume format DDMMYY
            day = int(date_str[:2])
            month = int(date_str[2:4])
            year = 2000 + int(date_str[4:6])
            metadata["date"] = f"{year}-{month:02d}-{day:02d}"
        except:
            pass
    
    # Detect type from filename
    if "Capsule" in filename:
        metadata["type"] = "capsule"
    elif "Podcast" in filename:
        metadata["type"] = "podcast"
    elif "Script" in filename:
        metadata["type"] = "script"
    elif "Conférence" in filename or "Conference" in filename:
        metadata["type"] = "conference"
    elif "Plan" in filename:
        metadata["type"] = "plan"
    else:
        metadata["type"] = "transcript"
    
    return metadata


def extract_reference_links(content: str) -> list:
    """Extract reference links (PMID) from content."""
    # Find all PMID patterns (e.g., "PMID: 27050205" or "PMID:31139631")
    pmid_pattern = r'PMID\s*:\s*(\d+)'
    links = re.findall(pmid_pattern, content, re.IGNORECASE)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links


def extract_sections(content: str) -> list:
    """Extract sections and subsections from content."""
    sections = []
    current_section = None
    current_subsection = None
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect main sections (numbered like "1. Introduction")
        section_match = re.match(r'^(\d+)\.\s+(.+)$', line)
        if section_match:
            # Save previous section
            if current_section:
                sections.append(current_section)
            
            current_section = {
                "number": section_match.group(1),
                "title": section_match.group(2),
                "content": [],
                "subsections": []
            }
            current_subsection = None
            continue
        
        # Detect subsections (words ending with colon or bullet points)
        if line.endswith(':') or line.startswith('•') or line.startswith('-'):
            subsection_title = line.rstrip(':').lstrip('•-').strip()
            if current_section:
                current_subsection = {
                    "title": subsection_title,
                    "content": []
                }
                current_section["subsections"].append(current_subsection)
            continue
        
        # Regular content
        if current_subsection:
            current_subsection["content"].append(line)
        elif current_section:
            current_section["content"].append(line)
    
    # Save last section
    if current_section:
        sections.append(current_section)
    
    return sections


def process_transcript_file(file_path: Path) -> dict:
    """Process a single transcript file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        metadata = extract_metadata_from_filename(file_path.name)
        
        # Extract first line as potential title
        lines = content.split('\n')
        first_line = lines[0].strip() if lines else ""
        if first_line and len(first_line) < 100:
            metadata["title"] = first_line
        
        # Extract sections
        sections = extract_sections(content)
        
        # Extract reference links (PMID)
        reference_links = extract_reference_links(content)
        
        # Calculate statistics
        word_count = len(content.split())
        char_count = len(content)
        line_count = len([l for l in lines if l.strip()])
        
        return {
            "reference": file_path.stem,
            "metadata": metadata,
            "statistics": {
                "words": word_count,
                "characters": char_count,
                "lines": line_count,
                "sections": len(sections)
            },
            "links": reference_links,
            "full_text": content,
            "sections": sections,
            "extracted_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error processing {file_path.name}: {str(e)}")
        return None


def create_chromadb_format(transcripts: list, kb_name: str) -> dict:
    """Create a ChromaDB-compatible format from transcripts."""
    documents = []
    doc_counter = 0  # Global counter to ensure unique IDs
    
    for transcript in transcripts:
        # Get common metadata
        base_metadata = {
            "source": transcript["metadata"]["filename"],
            "reference": transcript["reference"],
            "type": transcript["metadata"]["type"],
        }
        
        # Add optional metadata
        if transcript["metadata"].get("date"):
            base_metadata["date"] = transcript["metadata"]["date"]
        if transcript["metadata"].get("title"):
            base_metadata["title"] = transcript["metadata"]["title"]
        
        # Add reference links as comma-separated string for easier filtering
        if transcript.get("links"):
            base_metadata["links"] = ",".join(transcript["links"])
            base_metadata["link_count"] = len(transcript["links"])
        
        # If there are sections, create a document for each section
        if transcript["sections"]:
            for idx, section in enumerate(transcript["sections"]):
                section_text = f"Section {section['number']}: {section['title']}\n\n"
                
                # Add section content
                if section.get("content"):
                    section_text += "\n".join(section["content"]) + "\n\n"
                
                # Add subsections
                for subsection in section.get("subsections", []):
                    section_text += f"{subsection['title']}\n"
                    if subsection.get("content"):
                        section_text += "\n".join(subsection["content"]) + "\n\n"
                
                # Use global counter to ensure unique IDs
                doc_id = f"doc_{doc_counter:04d}_{transcript['reference']}_section{section['number']}"
                doc_counter += 1
                
                documents.append({
                    "id": doc_id,
                    "text": section_text.strip(),
                    "metadata": {
                        **base_metadata,
                        "section_number": section["number"],
                        "section_title": section["title"]
                    }
                })
        else:
            # No sections, use full text
            doc_id = f"doc_{doc_counter:04d}_{transcript['reference']}"
            doc_counter += 1
            
            documents.append({
                "id": doc_id,
                "text": transcript["full_text"],
                "metadata": base_metadata
            })
    
    return {
        "knowledge_base": kb_name,
        "format": "chromadb",
        "total_documents": len(documents),
        "extracted_at": datetime.now().isoformat(),
        "documents": documents
    }


def main():
    """Main execution function."""
    # Get knowledge base name from args or use default
    kb_name = sys.argv[1] if len(sys.argv) > 1 else "nutria"
    
    # Define paths
    project_root = Path(__file__).parent.parent.parent.parent
    transcripts_dir = project_root / "knowledge-bases" / kb_name / "transcripts"
    output_dir = project_root / "knowledge-bases" / kb_name 
    chromadb_file = output_dir / "transcripts_chromadb.json"
    
    # Verify directories exist
    if not transcripts_dir.exists():
        print(f"ERROR: Transcripts directory not found: {transcripts_dir}")
        sys.exit(1)
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing transcripts from: {transcripts_dir}")
    print(f"Output will be saved to: {chromadb_file}")
    print("-" * 60)
    
    # Process all transcript files
    transcripts = []
    txt_files = list(transcripts_dir.glob("*.txt"))
    
    if not txt_files:
        print("No .txt files found in transcripts directory")
        sys.exit(1)
    
    for file_path in sorted(txt_files):
        print(f"Processing: {file_path.name}")
        result = process_transcript_file(file_path)
        if result:
            transcripts.append(result)
    
    # Create output structure
    output_data = {
        "knowledge_base": kb_name,
        "extracted_at": datetime.now().isoformat(),
        "total_transcripts": len(transcripts),
        "transcripts_directory": str(transcripts_dir.relative_to(project_root)),
        "transcripts": transcripts,
        "summary": {
            "total_words": sum(t["statistics"]["words"] for t in transcripts),
            "total_characters": sum(t["statistics"]["characters"] for t in transcripts),
            "total_sections": sum(t["statistics"]["sections"] for t in transcripts),
            "types": {}
        }
    }
    
    # Count by type
    for transcript in transcripts:
        t_type = transcript["metadata"]["type"]
        output_data["summary"]["types"][t_type] = output_data["summary"]["types"].get(t_type, 0) + 1
    
    # Create and save ChromaDB-compatible format
    chromadb_data = create_chromadb_format(transcripts, kb_name)
    with open(chromadb_file, 'w', encoding='utf-8') as f:
        json.dump(chromadb_data, f, ensure_ascii=False, indent=2)
    
    print("-" * 60)
    print(f"✅ Successfully processed {len(transcripts)} transcripts")
    print(f"📄 ChromaDB format: {chromadb_file}")
    print(f"📊 Total words: {output_data['summary']['total_words']:,}")
    print(f"📊 Total sections: {output_data['summary']['total_sections']}")
    print(f"📊 Total documents for indexing: {chromadb_data['total_documents']}")
    print(f"📊 Types: {output_data['summary']['types']}")


if __name__ == "__main__":
    main()
