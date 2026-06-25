#!/usr/bin/env python3
"""
Fix: Add not-found.tsx to generated projects to prevent <Html> build error
Next.js 15.5.19 static export requires not-found.tsx in App Router
"""
import os, re

PROJECTS_DIR = "/data/projects"
MORGAN_ROUTE = "/root/buildany/src/app/api/morgan-generate/route.ts"

def add_not_found_to_morgan_generate():
    """Add not-found.tsx generation after the fallback page creation"""
    
    with open(MORGAN_ROUTE, 'r') as f:
        content = f.read()
    
    # Find the fallback page creation and add not-found.tsx after it
    old_pattern = '''      if (writtenFiles.length === 0) {
        const fallbackPage = path.join(projectDir, "src", "app", "page.tsx");
        await fs.writeFile(fallbackPage, `// @ts-nocheck\nexport default function Home() { return <div>Hello from ${shortName}</div>; }`);
        writtenFiles.push("src/app/page.tsx");
      }'''
    
    new_code = '''      if (writtenFiles.length === 0) {
        const fallbackPage = path.join(projectDir, "src", "app", "page.tsx");
        await fs.writeFile(fallbackPage, `// @ts-nocheck\nexport default function Home() { return <div>Hello from ${shortName}</div>; }`);
        writtenFiles.push("src/app/page.tsx");
      }

      // Add not-found.tsx for App Router (prevents Next.js 15 <Html> build error during static export)
      const notFoundPath = path.join(projectDir, "src", "app", "not-found.tsx");
      if (!writtenFiles.some(f => f.includes("not-found"))) {
        await fs.writeFile(notFoundPath, `// @ts-nocheck\nexport default function NotFound() {\n  return (\n    <div className="flex min-h-screen items-center justify-center">\n      <div className="text-center">\n        <h1 className="text-4xl font-bold mb-4">404</h1>\n        <p className="text-gray-600">Page not found</p>\n      </div>\n    </div>\n  );\n}\n`);
        writtenFiles.push("src/app/not-found.tsx");
      }'''
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_code)
        print("✅ Added not-found.tsx generation to morgan-generate route")
    else:
        print("⚠️ Could not find fallback pattern. Checking for alternative...")
        # Try alternative pattern
        alt_pattern = 'if (writtenFiles.length === 0) {'
        if alt_pattern in content:
            # Find the end of the if block and add after it
            idx = content.find(alt_pattern)
            # Find the closing brace of the if block
            brace_count = 0
            end_idx = idx
            for i in range(idx, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            insert_code = '''\n\n      // Add not-found.tsx for App Router (prevents Next.js 15 <Html> build error during static export)
      const notFoundPath = path.join(projectDir, "src", "app", "not-found.tsx");
      if (!writtenFiles.some(f => f.includes("not-found"))) {
        await fs.writeFile(notFoundPath, `// @ts-nocheck\nexport default function NotFound() {\n  return (\n    <div className="flex min-h-screen items-center justify-center">\n      <div className="text-center">\n        <h1 className="text-4xl font-bold mb-4">404</h1>\n        <p className="text-gray-600">Page not found</p>\n      </div>\n    </div>\n  );\n}\n`);
        writtenFiles.push("src/app/not-found.tsx");
      }'''
            
            content = content[:end_idx] + insert_code + content[end_idx:]
            print("✅ Added not-found.tsx generation (alternative method)")
        else:
            print("❌ Could not find insertion point")
            return False
    
    with open(MORGAN_ROUTE, 'w') as f:
        f.write(content)
    
    return True

def fix_existing_project(project_id):
    """Add not-found.tsx to an existing broken project"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    not_found_path = os.path.join(project_dir, "src", "app", "not-found.tsx")
    
    if os.path.exists(not_found_path):
        print(f"Project {project_id}: not-found.tsx already exists")
        return True
    
    not_found_content = '''// @ts-nocheck
export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">404</h1>
        <p className="text-gray-600">Page not found</p>
      </div>
    </div>
  );
}
'''
    
    try:
        os.makedirs(os.path.dirname(not_found_path), exist_ok=True)
        with open(not_found_path, 'w') as f:
            f.write(not_found_content)
        print(f"✅ Project {project_id}: Added not-found.tsx")
        return True
    except Exception as e:
        print(f"❌ Project {project_id}: Failed to add not-found.tsx: {e}")
        return False

def rebuild_project(project_id):
    """Rebuild a specific project"""
    import subprocess
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_dir):
        print(f"Project {project_id}: Directory not found")
        return False
    
    try:
        # Update DB status to building
        import sqlite3
        db = sqlite3.connect('/root/buildany/sqlite.db')
        db.execute("UPDATE projects SET status = 'building' WHERE id = ?", (project_id,))
        db.commit()
        db.close()
        
        # Run build
        print(f"Project {project_id}: Running npm install...")
        subprocess.run(['npm', 'install'], cwd=project_dir, check=True, capture_output=True)
        
        print(f"Project {project_id}: Running next build...")
        result = subprocess.run(['npx', 'next', 'build'], cwd=project_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Project {project_id}: Build successful!")
            # Update DB status
            db = sqlite3.connect('/root/buildany/sqlite.db')
            db.execute("UPDATE projects SET status = 'ready' WHERE id = ?", (project_id,))
            db.commit()
            db.close()
            return True
        else:
            print(f"❌ Project {project_id}: Build failed")
            print(result.stderr[:500])
            # Update DB status
            db = sqlite3.connect('/root/buildany/sqlite.db')
            db.execute("UPDATE projects SET status = 'build_failed' WHERE id = ?", (project_id,))
            db.commit()
            db.close()
            return False
    except Exception as e:
        print(f"❌ Project {project_id}: Error during rebuild: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Fixing Next.js 15 <Html> build error")
    print("="*60)
    
    # Fix morgan-generate route
    print("\n1. Updating morgan-generate route...")
    add_not_found_to_morgan_generate()
    
    # Fix existing broken project
    print("\n2. Fixing existing project 8d3d584a...")
    fix_existing_project("8d3d584a-bb6a-4a78-ad27-53f434f9faf5")
    
    # Rebuild project
    print("\n3. Rebuilding project...")
    rebuild_project("8d3d584a-bb6a-4a78-ad27-53f434f9faf5")
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)
