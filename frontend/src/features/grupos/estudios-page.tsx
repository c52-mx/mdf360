import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Button,
  Card,
  CardDescription,
  CardTitle,
  Field,
  FileButton,
  PageHeader,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api, apiForm } from '@/lib/api'
import { fechaLarga, type Estudio } from './types'

const hoy = () => new Date().toISOString().slice(0, 10)

export function EstudiosPage() {
  const queryClient = useQueryClient()
  const puedeSubir = useCan('grupos.material')
  const [titulo, setTitulo] = useState('')
  const [semana, setSemana] = useState(hoy())
  const [adultos, setAdultos] = useState<File | null>(null)
  const [ninos, setNinos] = useState<File | null>(null)
  const [audio, setAudio] = useState<File | null>(null)

  const estudios = useQuery({
    queryKey: ['estudios'],
    queryFn: () => api<Estudio[]>('/api/grupos/estudios/'),
  })
  const subir = useMutation({
    mutationFn: () => {
      const form = new FormData()
      form.append('titulo', titulo)
      form.append('semana', semana)
      if (adultos) form.append('pdf_adultos', adultos)
      if (ninos) form.append('pdf_ninos', ninos)
      if (audio) form.append('audio', audio)
      return apiForm<Estudio>('/api/grupos/estudios/', form)
    },
    onSuccess: () => {
      setTitulo('')
      setAdultos(null)
      setNinos(null)
      setAudio(null)
      void queryClient.invalidateQueries({ queryKey: ['estudios'] })
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    subir.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Estudio de la semana"
        description="PDF para adultos, PDF para niños y audio de la lectura."
        module="grupos"
      />

      {puedeSubir ? (
        <Card>
          <form onSubmit={onSubmit} className="grid max-w-xl grid-cols-1 gap-4">
            <CardTitle>Publicar o actualizar un estudio</CardTitle>
            <Field label="Título" value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
            <Field
              label="Semana"
              type="date"
              hint="Cualquier día de la semana; se publica para esa semana."
              value={semana}
              onChange={(e) => setSemana(e.target.value)}
              required
            />
            <div className="flex flex-wrap items-center gap-3">
              <FileButton accept="application/pdf" onFile={setAdultos}>
                PDF adultos
              </FileButton>
              <span className="text-muted-foreground">{adultos?.name ?? 'Sin archivo'}</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <FileButton accept="application/pdf" onFile={setNinos}>
                PDF niños
              </FileButton>
              <span className="text-muted-foreground">{ninos?.name ?? 'Sin archivo'}</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <FileButton accept="audio/*" onFile={setAudio}>
                Audio
              </FileButton>
              <span className="text-muted-foreground">{audio?.name ?? 'Sin archivo'}</span>
            </div>
            <CardDescription>
              PDF hasta 15 MB y audio hasta 40 MB (mp3, m4a, aac, ogg, opus o wav).
            </CardDescription>
            {subir.isSuccess ? <Alert tone="success">Estudio guardado.</Alert> : null}
            {subir.error ? <Alert tone="destructive">{subir.error.message}</Alert> : null}
            <Button type="submit" disabled={subir.isPending}>
              {subir.isPending ? 'Subiendo…' : 'Guardar estudio'}
            </Button>
          </form>
        </Card>
      ) : null}

      {estudios.isError ? <Alert tone="destructive">{estudios.error.message}</Alert> : null}
      <ul className="flex flex-col gap-3">
        {estudios.data?.map((e) => (
          <li key={e.id}>
            <Card className="flex flex-col gap-3">
              <div>
                <CardTitle>{e.titulo}</CardTitle>
                <CardDescription>Semana del {fechaLarga(e.semana)}</CardDescription>
              </div>
              {e.audio ? <audio controls preload="none" src={e.audio} className="w-full" /> : null}
              <div className="flex flex-wrap gap-3">
                {e.pdf_adultos ? (
                  <Button asChild variant="outline">
                    <a href={e.pdf_adultos} target="_blank" rel="noreferrer">
                      PDF adultos
                    </a>
                  </Button>
                ) : null}
                {e.pdf_ninos ? (
                  <Button asChild variant="outline">
                    <a href={e.pdf_ninos} target="_blank" rel="noreferrer">
                      PDF niños
                    </a>
                  </Button>
                ) : null}
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  )
}
