<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import AppDialog from '@/shared/components/AppDialog.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Tag from '@/volt/Tag.vue'
import { demandsApi } from '../api'
import { displayDate, fileSize, historyLabel, kindLabel, statusLabel } from '../presentation'
import type { RequestDetail } from '../types'
import RequestForm from './RequestForm.vue'
import RequestReviewForm from './RequestReviewForm.vue'

const props = defineProps<{ id: number; management?: boolean }>()
const emit = defineEmits<{ closed: []; changed: []; busy: [value: boolean] }>()
const editing = ref(false)
const busy = ref(false)
const visible = ref(true)
const reviewKey = ref(0)
const reviewFeedback = ref('')
watch(busy, value => emit('busy', value), { flush: 'sync' })
const client = useQueryClient()
const queryKey = props.management ? ['demands', 'management', 'detail', props.id] : ['demands', 'detail', props.id]
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey, queryFn: () => props.management ? demandsApi.managementGet(props.id) : demandsApi.get(props.id), retry: false,
  refetchOnWindowFocus: false, refetchOnReconnect: false,
})
const details = [
  { key: 'assumptions', label: 'Premissas' },
  { key: 'current_problems', label: 'Problemas atuais' },
  { key: 'expected_benefits', label: 'Ganhos esperados' },
] as const

function close() { if (!busy.value) visible.value = false }
function saved(request: RequestDetail) {
  client.setQueryData(queryKey, request)
  editing.value = false
  emit('changed')
}
async function reloadReview() {
  reviewFeedback.value = ''
  busy.value = true
  try {
    const result = await refetch()
    if (result.isSuccess) reviewKey.value += 1
  } finally {
    busy.value = false
  }
}
async function reviewed(request: RequestDetail) {
  reviewFeedback.value = request.status === 'a_fazer' ? 'Solicitação aceita e responsável definido.'
    : request.status === 'recusado' ? 'Solicitação recusada. O motivo foi registrado no histórico.'
      : 'Pedido de informações registrado no histórico. Aguardando complemento do solicitante.'
  saved(request)
  void client.invalidateQueries({ queryKey: ['demands', 'detail', props.id] })
  await nextTick()
  document.getElementById('request-review-feedback-' + props.id)?.focus()
}
</script>

<template>
  <AppDialog :id="'request-dialog-' + id" :visible="visible" :title="'Solicitação #' + id"
    :subtitle="editing ? 'Editar os dados enviados' : management ? 'Confira os dados e analise a solicitação recebida' : 'Acompanhe os detalhes da sua solicitação'"
    icon="pi pi-inbox" :busy="busy" @update:visible="close" @closed="emit('closed')">
    <RequestForm v-if="editing && data" :request="data" @saved="saved" @busy="busy = $event" @cancel="editing = false" />
    <RequestState v-else :loading="isPending" :failed="isError" :error="error" :empty="false"
      loading-label="Carregando solicitação…" error-message="Não foi possível carregar a solicitação."
      not-found-message="Solicitação não encontrada para seu acesso." @retry="refetch()">
      <div v-if="data">
        <div class="flex flex-wrap items-center gap-2">
          <Tag :value="statusLabel(data.status)" severity="secondary" />
          <Tag :value="kindLabel(data.entry_kind)" />
        </div>
        <h3 class="mt-4 break-words text-xl font-semibold text-dj-ink">{{ data.title }}</h3>
        <dl class="mt-5 grid gap-4 rounded-2xl border border-dj-border bg-dj-canvas p-4 text-sm sm:grid-cols-2">
          <div><dt class="text-xs text-dj-muted">Solicitante</dt><dd class="mt-1">{{ data.requester_name ?? 'Não informado' }}</dd></div>
          <div><dt class="text-xs text-dj-muted">Contribuinte</dt><dd class="mt-1">{{ data.contributor_name ?? 'Sem contribuinte' }}</dd></div>
          <div><dt class="text-xs text-dj-muted">Urgência</dt><dd class="mt-1">{{ data.urgency }}</dd></div>
          <div><dt class="text-xs text-dj-muted">Enviada em</dt><dd class="mt-1">{{ displayDate(data.created_at) }}</dd></div>
          <div v-if="data.responsible_id"><dt class="text-xs text-dj-muted">Responsável</dt><dd class="mt-1">{{ data.responsible_name ?? 'Usuário indisponível' }}</dd></div>
          <div v-if="data.classification"><dt class="text-xs text-dj-muted">Classificação</dt><dd class="mt-1">{{ data.classification === 'projeto' ? 'Projeto' : data.classification === 'melhoria' ? 'Melhoria' : data.classification }}</dd></div>
          <div><dt class="text-xs text-dj-muted">Atualizada em</dt><dd class="mt-1">{{ displayDate(data.updated_at) }}</dd></div>
        </dl>
        <section class="mt-6" :aria-labelledby="'request-description-' + id">
          <h4 :id="'request-description-' + id" class="mb-2 text-sm font-semibold">{{ data.entry_kind === 'erro' ? 'Descrição do erro' : 'Objetivo da demanda' }}</h4>
          <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-muted">{{ data.description }}</p>
        </section>
        <template v-if="data.entry_kind === 'demanda'">
          <section v-for="field in details" :key="field.key" class="mt-5" :aria-labelledby="'request-' + id + '-' + field.key">
            <h4 :id="'request-' + id + '-' + field.key" class="mb-2 text-sm font-semibold">{{ field.label }}</h4>
            <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-muted">{{ data[field.key] ?? 'Não informado' }}</p>
          </section>
        </template>
        <section class="mt-6" :aria-labelledby="'request-attachments-' + id">
          <h4 :id="'request-attachments-' + id" class="mb-3 text-sm font-semibold">Documentos</h4>
          <ul class="space-y-2">
            <li v-for="attachment in data.attachments" :key="attachment.id">
              <a :href="demandsApi.attachmentUrl(id, attachment.id, management)" class="inline-flex max-w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-dj-brand underline underline-offset-4">
                <i class="pi pi-download shrink-0" aria-hidden="true" />
                <span class="min-w-0 break-words">{{ attachment.original_name }} ({{ fileSize(attachment.size_bytes) }})</span>
              </a>
            </li>
          </ul>
          <p v-if="!data.attachments.length" class="text-sm text-dj-muted">Nenhum documento disponível.</p>
        </section>
        <section class="mt-6 border-t border-dj-border pt-5" :aria-labelledby="'request-history-' + id">
          <h4 :id="'request-history-' + id" class="mb-3 text-sm font-semibold">Histórico</h4>
          <ol class="space-y-3 text-sm">
            <li v-for="event in data.history" :key="event.id" class="border-l-2 border-dj-border pl-3">
              <p>{{ historyLabel(event.event_type) }}</p>
              <p v-if="event.message" class="mt-2 whitespace-pre-wrap break-words leading-7 text-dj-muted">{{ event.message }}</p>
              <p class="mt-1 text-xs text-dj-muted">{{ event.actor_name ?? 'Usuário indisponível' }} · {{ displayDate(event.created_at) }}</p>
            </li>
          </ol>
        </section>
        <p v-if="management && reviewFeedback" :id="'request-review-feedback-' + id" tabindex="-1" role="status"
          class="mt-6 rounded-xl border border-dj-border bg-dj-canvas p-4 text-sm">{{ reviewFeedback }}</p>
        <RequestReviewForm v-if="management && data.can_review" :key="data.row_version + '-' + reviewKey" :request="data" :disabled="busy"
          @saved="reviewed" @busy="busy = $event" @reload="reloadReview" />
        <p v-else-if="management && !reviewFeedback" tabindex="-1"
          class="mt-6 rounded-xl border border-dj-border bg-dj-canvas p-4 text-sm">
          {{ data.status === 'a_fazer' ? 'Solicitação aceita e responsável definido.' : data.status === 'recusado' ? 'Solicitação recusada. O motivo está registrado no histórico.' : 'Esta solicitação já foi analisada.' }}
        </p>
      </div>
    </RequestState>
    <template v-if="!editing" #footer>
      <Button v-if="data?.can_update && !isError" type="button" label="Editar solicitação" icon="pi pi-pencil" @click="editing = true" />
      <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" @click="close" />
    </template>
  </AppDialog>
</template>
