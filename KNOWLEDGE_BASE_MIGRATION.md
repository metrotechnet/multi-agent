# Knowledge Base System Migration Guide

## Overview

The imx-multi-agent project has been restructured to support multiple knowledge bases. This guide documents the changes and how to work with the new system.

## What Changed

### Before (Old Structure)
```
imx-multi-agent/
├── transcripts/       # All transcripts
├── documents/         # All documents
├── extracted_texts/   # All extracted texts
└── chroma_db/         # Single ChromaDB database
```

### After (New Structure)
```
imx-multi-agent/
└── knowledge-bases/
    ├── nutria/               # Default knowledge base
    │   ├── transcripts/
    │   ├── documents/
    │   ├── extracted_texts/
    │   ├── chroma_db/
    │   └── prompts.json      # KB-specific prompts
    └── other-kb/             # Additional knowledge bases
        ├── transcripts/
        ├── documents/
        ├── extracted_texts/
        ├── chroma_db/
        └── prompts.json      # Different prompts for this KB
```

## Migration Steps

All data from the old structure has been automatically migrated to `knowledge-bases/nutria/`.

### Files Modified

1. **scripts/index_chromadb.py**
   - Now accepts knowledge base name as parameter
   - Usage: `python scripts/index_chromadb.py <kb-name> <folder-type>`
   - Default: `python scripts/index_chromadb.py nutria extracted_texts`

2. **core/query_chromadb.py**
   - Added `KNOWLEDGE_BASE` environment variable support
   - `get_collection()` function now accepts optional `kb_name` parameter
   - Automatic path resolution to knowledge base folders

3. **core/pipeline_gdrive.py**
   - Updated to use knowledge base paths
   - Respects `KNOWLEDGE_BASE` environment variable
   - Documents indexed to active knowledge base

4. **Prompts Configuration**
   - Moved `prompts.json` from `config/` to `knowledge-bases/nutria/`
   - Each knowledge base can now have its own prompts
   - Application loads prompts from active knowledge base
   - Falls back to `config/prompts.json` if not found (backward compatible)

5. **.env**
   - Added: `KNOWLEDGE_BASE=nutria`
   - This sets which knowledge base the application uses

## New Features

### 1. Multiple Knowledge Bases

Create and manage separate knowledge bases for different domains:

```powershell
# Create new knowledge base
.\scripts\create_knowledge_base.ps1 -Name "medical-kb"

# Add documents
cp *.txt knowledge-bases\medical-kb\extracted_texts\

# Index
python scripts\index_chromadb.py medical-kb extracted_texts
```

### 2. Easy Switching

Switch between knowledge bases by updating `.env`:

```env
# Use nutrition knowledge base
KNOWLEDGE_BASE=nutria

# Or use medical knowledge base
KNOWLEDGE_BASE=medical-kb
```

Then restart the application.

### 3. Helper Scripts

- **create_knowledge_base.ps1**: Creates new knowledge base structure
- **Knowledge base README**: Each KB can have its own README

### 4. Improved Organization

- Each knowledge base is self-contained
- Easier to backup/restore individual knowledge bases
- Clear separation of different document sets
- **Knowledge base-specific prompts**: Each KB can have customized AI behavior

### 5. Custom Prompts per Knowledge Base

Each knowledge base can now have its own `prompts.json` file:

```powershell
# Copy and customize prompts for a new KB
Copy-Item knowledge-bases\nutria\prompts.json knowledge-bases\medical-kb\prompts.json

# Edit the prompts to match the KB's domain
notepad knowledge-bases\medical-kb\prompts.json
```

The application automatically loads prompts from the active knowledge base, allowing you to:
- Customize AI tone and style per domain
- Set different behavioral rules for each KB
- Maintain separate instructions for different use cases

## Backward Compatibility

The migration was done automatically and preserves all existing data:

- ✅ All 843 documents from old `chroma_db/` are now in `knowledge-bases/nutria/chroma_db/`
- ✅ All transcripts moved to `knowledge-bases/nutria/transcripts/`
- ✅ All documents moved to `knowledge-bases/nutria/documents/`
- ✅ All extracted texts moved to `knowledge-bases/nutria/extracted_texts/`
- ✅ Application still works with default settings

No reindexing is required - the existing database was moved intact.

## Usage Examples

### Index a Knowledge Base

```bash
# Index default knowledge base (nutria)
python scripts/index_chromadb.py

# Index specific knowledge base
python scripts/index_chromadb.py medical-kb extracted_texts

# Index transcripts folder
python scripts/index_chromadb.py nutria transcripts
```

### Query a Specific Knowledge Base

```python
from core.query_chromadb import get_collection

# Get default knowledge base (from .env)
col = get_collection()

# Get specific knowledge base
col = get_collection('medical-kb')

print(f"Documents: {col.count()}")
```

### Google Drive Pipeline

The pipeline respects the active knowledge base:

```python
from core.pipeline_gdrive import run_pipeline

# Downloads and indexes to active knowledge base
result = run_pipeline()
```

## Verifying the Migration

Check that everything is working:

```powershell
# 1. Check folder structure
Get-ChildItem knowledge-bases\nutria -Directory

# 2. Verify database loads
python -c "from core.query_chromadb import get_collection; col = get_collection(); print(f'Documents: {col.count()}')"

# 3. Test the application
.\start_server.ps1
# Navigate to http://localhost:8080
```

Expected output:
- ✅ 4 folders in `knowledge-bases/nutria/`
- ✅ 843 documents in collection
- ✅ Application starts without errors

## Troubleshooting

### Issue: "ChromaDB path not found"

**Solution**: The knowledge base hasn't been indexed yet.

```bash
python scripts/index_chromadb.py nutria extracted_texts
```

### Issue: Empty search results

**Solution**: Verify documents exist and are indexed.

```powershell
# Check files exist
Get-ChildItem knowledge-bases\nutria\extracted_texts

# Check database count
python -c "from core.query_chromadb import get_collection; print(get_collection().count())"
```

### Issue: Application uses wrong knowledge base

**Solution**: Check `.env` file has correct `KNOWLEDGE_BASE` value and restart the app.

```env
KNOWLEDGE_BASE=nutria
```

## Benefits of New System

1. **Modularity**: Easy to create domain-specific agents
2. **Isolation**: Knowledge bases don't interfere with each other
3. **Scalability**: Add unlimited knowledge bases without conflicts
4. **Maintenance**: Easier to backup, restore, and manage data
5. **Development**: Test with different datasets without affecting production
6. **Multi-tenancy**: Deploy same codebase with different knowledge bases

## Advanced Usage

### Programmatic KB Switching

```python
import os
os.environ['KNOWLEDGE_BASE'] = 'medical-kb'

from core.query_chromadb import get_collection
col = get_collection()  # Uses medical-kb
```

### Multiple Collections

Each knowledge base has its own ChromaDB instance, so you can query multiple simultaneously:

```python
from core.query_chromadb import get_collection

# Query nutrition KB
nutrition_col = get_collection('nutria')

# Query medical KB  
medical_col = get_collection('medical-kb')

# Combine results
combined_results = []
combined_results.extend(nutrition_col.query(...))
combined_results.extend(medical_col.query(...))
```

## Documentation

- **knowledge-bases/README.md**: Complete knowledge base documentation
- **README.md**: Updated project documentation
- **scripts/create_knowledge_base.ps1**: Helper script with inline help

## Support

If you encounter issues:

1. Check this migration guide
2. Review `knowledge-bases/README.md`
3. Verify `.env` configuration
4. Check application logs for error messages
5. Run verification commands above

---

**Migration Date**: February 17, 2026  
**Status**: ✅ Complete  
**Data Preserved**: 100% (843 documents)  
**Backward Compatible**: Yes
