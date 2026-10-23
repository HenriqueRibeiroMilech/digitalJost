<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import AppDialog from '@/shared/components/AppDialog.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Tag from '@/volt/Tag.vue'
import Message from '@/volt/Message.vue'
import Tabs from '@/volt/Tabs.vue'
import Tab from '@/volt/Tab.vue'
import TabList from '@/volt/TabList.vue'
import TabPanels from '@/volt/TabPanels.vue'
import TabPanel from '@/volt/TabPanel.vue'
import ManagementEditor from './ManagementEditor.vue'
import ManagementAction from './ManagementAction.vue'
import ManagementTasks from './ManagementTasks.vue'
import DemandHistory from './DemandHistory.vue'
import DemandInformation from './DemandInformation.vue'
import { managementApi } from '../managementApi'
import { blankManagementFields, dayLabel, demandTypeLabel } from '../managementTypes'
import type { ManagedDetail, ManagementOptions } from '../managementTypes'
import { fileAccept, fileSize, statusLabel } from '../presentation'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
const props = defineProps<{ id: number; options: ManagementOptions }>()
const emit = defineEmits<{ closed: []; changed: []; busy: [value: boolean] }>()
const visible = ref(true); const busy = ref(false); const childBusy = ref(false); const editing = ref(false); const otherOpen = ref(false)
const tab = ref('info'); const action = ref<string | null>(null); const error = ref(''); const warning = ref('')
const fields = ref(blankManagementFields()); const files = ref<File[]>([]); const removing = ref<number | null>(null)
const fieldErrors = ref<Record<string, string>>({})
const client = useQueryClient(); const queryKey = ['demands', 'management-detail', props.id]
const { data, isPending, isError, error: loadError, refetch } = useQuery({ queryKey, queryFn: () => managementApi.get(props.id),
  retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const locked = computed(() => busy.value || childBusy.value)
watch(locked, value => emit('busy', value), { flush: 'sync' })
const reviewable = computed(() => data.value?.origin === 'solicitacao' && !data.value.responsible_id && ['em_analise', 'aguardando_informacoes'].includes(data.value.status))
const labels: Record<string, string> = { start: 'Iniciar', complete: 'Concluir', cancel: 'Cancelar', resume: 'Retomar', schedule: 'Agendar início', unschedule: 'Cancelar agendamento',
  information: 'Solicitar mais informações ou reunião', validate: 'Iniciar validação', pause: 'Pausar', third_party: 'Aguardando terceiros' }
const primary = computed(() => {
  const status = data.value?.status
  if (status === 'a_fazer') return ['start', 'cancel']
  if (status === 'em_andamento') return ['complete', 'cancel']
  if (status === 'em_validacao') return ['complete', 'resume', 'cancel']
  if (status === 'pausado' || status === 'aguardando_terceiros') return ['resume', 'cancel']
  return status === 'aguardando_informacoes' ? ['cancel'] : []
})
const others = computed(() => {
  if (data.value?.status === 'a_fazer') return ['schedule', ...(data.value.scheduled_start_date ? ['unschedule'] : []), 'information']
  if (data.value?.status === 'em_andamento') return ['information', 'validate', 'pause', 'third_party']
  if (['pausado', 'aguardando_terceiros', 'em_validacao'].includes(data.value?.status ?? '')) return ['information']
  return []
})
const sections = [{ key: 'assumptions', label: 'Premissas' }, { key: 'current_problems', label: 'Problemas atuais' }, { key: 'expected_benefits', label: 'Ganhos esperados' }] as const
function changed(value: ManagedDetail) {
  client.setQueryData(queryKey, value); warning.value = value.notification_warning ?? ''; emit('changed')
}
function startEdit() { if (data.value) { fields.value = blankManagementFields('', data.value); fieldErrors.value = {}; editing.value = true } }
async function save() {
  if (!data.value || locked.value) return
  busy.value = true; error.value = ''; fieldErrors.value = {}
  try { changed(await managementApi.update(props.id, { ...fields.value, row_version: data.value.row_version })); editing.value = false }
  catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível salvar.'
    if (err instanceof ApiError) fieldErrors.value = validationMessages(err.detail, ['title', 'description', 'responsible_id', 'assumptions', 'current_problems', 'expected_benefits', 'estimated_hours', 'daily_hours', 'completed_hours', 'priority', 'observations'])
  }
  finally { busy.value = false }
}
async function attachment(remove?: number) {
  if (!data.value || locked.value) return
  busy.value = true; error.value = ''
  try {
    changed(remove ? await managementApi.removeAttachment(props.id, remove, data.value.row_version)
      : await managementApi.attach(props.id, data.value.row_version, files.value))
    files.value = []; removing.value = null
  } catch (err) {
    error.value = err instanceof ApiError ? validationMessages(err.detail, ['files']).files || err.message
      : err instanceof Error ? err.message : 'Não foi possível atualizar os documentos.'
  }
  finally { busy.value = false }
}
</script>
<template>
  <AppDialog :id="'management-detail-' + id" :visible="visible" :title="data?.title ?? 'Detalhes da demanda'" :subtitle="'Registro #' + id" icon="pi pi-briefcase" :busy="locked || !!action"
    @update:visible="visible = false" @closed="emit('closed')">
    <RequestState :loading="isPending" :failed="isError" :error="loadError" :empty="false" @retry="refetch()">
      <div v-if="data">
        <div class="mb-4 flex flex-wrap gap-2"><Tag :value="statusLabel(data.status)" severity="secondary" /><Tag :value="demandTypeLabel(data.demand_type)" />
          <Tag v-if="data.scheduled_start_date" value="Demanda agendada" severity="info" /></div>
        <Message v-if="warning" severity="warn" class="mb-4">{{ warning }}</Message>
        <Message v-if="error" severity="error" role="alert" class="mb-4">{{ error }}</Message>
        <Tabs v-model:value="tab">
          <TabList><Tab value="info" :disabled="locked || editing">Informações e gerenciamento</Tab><Tab value="tasks" :disabled="locked || editing">Tarefas</Tab><Tab value="history" :disabled="locked || editing">Histórico</Tab></TabList>
          <TabPanels>
            <TabPanel value="info">
              <div v-if="reviewable" class="mb-5 flex flex-wrap gap-2">
                <Button type="button" label="Aceitar" :disabled="locked" @click="action = 'accept'" />
                <SecondaryButton type="button" label="Recusar" outlined :disabled="locked" @click="action = 'decline'" />
                <SecondaryButton type="button" label="Solicitar informações ou reunião" outlined :disabled="locked || data.status === 'aguardando_informacoes'" @click="action = 'review_information'" />
              </div>
              <template v-else-if="data.can_edit && !editing">
                <div class="mb-3 flex flex-wrap gap-2">
                  <Button v-for="item in primary" :key="item" type="button" :label="labels[item]" :outlined="item === 'cancel'" :disabled="locked" @click="action = item" />
                  <SecondaryButton v-if="others.length" type="button" label="Outras ações" icon="pi pi-ellipsis-h" outlined :disabled="locked"
                    :aria-expanded="otherOpen" aria-controls="management-other-actions" @click="otherOpen = !otherOpen" />
                </div>
                <div v-if="otherOpen" id="management-other-actions" class="mb-5 flex flex-wrap gap-2 rounded-xl border border-dj-border p-3" role="group" aria-label="Outras ações">
                  <SecondaryButton v-for="item in others" :key="item" type="button" :label="labels[item]" :disabled="locked" @click="action = item; otherOpen = false" />
                </div>
              </template>
              <div class="mb-5 grid gap-4 rounded-xl bg-dj-canvas p-4 text-sm sm:grid-cols-2">
                <p>Solicitante: {{ data.requester_name ?? 'Não informado' }}</p><p>Responsável: {{ data.responsible_name ?? 'Não atribuído' }}</p>
                <p>Contribuinte: {{ data.contributor_name ?? 'Não informado' }}</p><p>Urgência: {{ data.urgency }}</p>
                <p>{{ data.scheduled_start_date ? 'Início agendado' : 'Início' }}: {{ dayLabel(data.scheduled_start_date ?? data.started_at) }}</p>
                <div class="flex flex-wrap items-center gap-3"><p>Prazo: {{ dayLabel(data.deadline) }}</p>
                  <SecondaryButton v-if="data.can_edit && !editing" type="button" label="Alterar prazo" text :disabled="locked" @click="action = 'deadline'" /></div>
              </div>
              <form v-if="editing" @submit.prevent="save">
                <ManagementEditor v-model="fields" :kind="data.demand_type ?? 'melhoria'" :options="options" :disabled="locked" :errors="fieldErrors" />
                <div class="my-5 flex gap-2"><SecondaryButton type="button" label="Cancelar edição" outlined :disabled="locked" @click="editing = false" /><Button type="submit" label="Salvar gerenciamento" :loading="busy" :disabled="locked" /></div>
              </form>
              <div v-else class="space-y-5">
                <p class="whitespace-pre-wrap break-words text-sm leading-7">{{ data.description }}</p>
                <section v-for="section in sections.filter(item => data?.[item.key])" :key="section.key"><h4 class="text-sm font-semibold">{{ section.label }}</h4><p class="mt-2 whitespace-pre-wrap break-words text-sm text-dj-muted">{{ data[section.key] }}</p></section>
                <dl class="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                  <div><dt class="text-xs text-dj-muted">Estimado / realizado</dt><dd>{{ data.estimated_hours ?? '—' }} / {{ data.completed_hours ?? '—' }} h</dd></div>
                  <div><dt class="text-xs text-dj-muted">Tempo diário</dt><dd>{{ data.daily_hours ?? '—' }} h</dd></div>
                  <div><dt class="text-xs text-dj-muted">Prioridade</dt><dd>{{ data.priority ?? 'Não informada' }}</dd></div>
                  <div><dt class="text-xs text-dj-muted">Dificuldade</dt><dd>{{ data.difficulty ?? 'Não informada' }}</dd></div>
                </dl>
                <p v-if="data.observations" class="whitespace-pre-wrap break-words text-sm text-dj-muted">{{ data.observations }}</p>
                <SecondaryButton v-if="data.can_edit" type="button" label="Editar informações e gerenciamento" icon="pi pi-pencil" outlined :disabled="locked" @click="startEdit" />
              </div>
              <DemandInformation :demand-id="id" :version="data.row_version" :items="data.information_requests" class="mt-5" />
              <section class="mt-6 border-t border-dj-border pt-5" aria-label="Documentos">
                <h4 class="mb-3 font-semibold">Anexos</h4>
                <ul class="space-y-3"><li v-for="file in data.attachments" :key="file.id" class="flex flex-wrap items-center justify-between gap-2">
                  <a :href="managementApi.attachmentUrl(id, file.id)" class="min-w-0 break-words text-sm text-dj-brand underline">{{ file.original_name }} ({{ fileSize(file.size_bytes) }})</a>
                  <SecondaryButton v-if="data.can_edit" type="button" label="Remover" text :disabled="locked" @click="removing = file.id" />
                  <div v-if="removing === file.id" class="flex w-full flex-wrap items-center gap-2 text-sm" role="alert">Remover este anexo?
                    <SecondaryButton type="button" label="Voltar" :disabled="locked" @click="removing = null" /><Button type="button" label="Confirmar remoção" :disabled="locked" @click="attachment(file.id)" /></div>
                </li></ul>
                <form v-if="data.can_edit" class="mt-4 flex flex-wrap items-end gap-3" @submit.prevent="attachment()">
                  <label class="text-sm">Adicionar documentos<input type="file" multiple :accept="fileAccept" :disabled="locked" class="mt-2 block max-w-full text-sm" @change="files = Array.from(($event.target as HTMLInputElement).files ?? [])" /></label>
                  <Button type="submit" label="Enviar anexos" :disabled="locked || !files.length" />
                </form>
              </section>
            </TabPanel>
            <TabPanel value="tasks"><ManagementTasks :demand="data" :options="options" @saved="changed" @busy="childBusy = $event" /></TabPanel>
            <TabPanel value="history"><DemandHistory :events="data.history" /></TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </RequestState>
    <template #footer><SecondaryButton type="button" label="Fechar" outlined :disabled="locked || !!action" @click="visible = false" /></template>
  </AppDialog>
  <ManagementAction v-if="data && action" :demand="data" :action="action" :options="options" @saved="changed" @closed="action = null" @busy="childBusy = $event" />
</template>
