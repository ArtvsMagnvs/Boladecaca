// pages/Workspace/index.tsx — WPMS: lienzo espacial de proyectos (V0.87 W2b)
//
// Pagina delgada: la lista de proyectos (CRUD) + el popup de proyecto viven
// aqui (una sola instancia compartida, editar un proyecto es lo mismo se abra
// desde la estantería o desde el header de una tarjeta); todo lo demas
// (milestones/tareas/agentes de CADA proyecto) vive dentro de su propia
// ProjectCard, cargado solo cuando esa tarjeta está fuera de la estantería.
import { useCallback, useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";
import { WorkspaceCanvas } from "./WorkspaceCanvas";
import { ProjectPopup } from "./ProjectPopup";

export default function Workspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectEdit, setProjectEdit] = useState<Project | null | undefined>(undefined);

  const loadProjects = useCallback(async () => {
    const ps = await api.getProjects();
    setProjects(ps);
    setLoading(false);
  }, []);

  useEffect(() => { loadProjects().catch(() => setLoading(false)); }, [loadProjects]);

  const saveProject = async (data: Partial<Project>) => {
    if (projectEdit) await api.updateProject(projectEdit.id, data);
    else await api.createProject(data);
    setProjectEdit(undefined);
    await loadProjects();
  };
  const deleteProject = async (id: number) => {
    await api.deleteProject(id);
    setProjectEdit(undefined);
    await loadProjects();
  };
  // V0.87 (WPMS W4, doc 18 §5.1): archivar, no borrar — el proyecto sigue
  // listado y consultable, solo deja de contar como activo.
  const archiveProject = async (id: number) => {
    await api.archiveProject(id);
    setProjectEdit(undefined);
    await loadProjects();
  };

  if (loading) {
    return <div className="h-full flex items-center justify-center text-ink-dim">Cargando…</div>;
  }

  return (
    <div className="h-full">
      <WorkspaceCanvas
        projects={projects}
        onCreateProject={() => setProjectEdit(null)}
        onEditProject={(p) => setProjectEdit(p)}
        onProjectsRefresh={loadProjects}
      />

      {projectEdit !== undefined && (
        <ProjectPopup
          project={projectEdit}
          onSave={saveProject}
          onDelete={deleteProject}
          onArchive={archiveProject}
          onClose={() => setProjectEdit(undefined)}
        />
      )}
    </div>
  );
}
