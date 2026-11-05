<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import { demandsApi } from '../api'
import type { RequestDetail, ReviewFields } from '../types'

const props = defineProps<{ request: RequestDetail; disabled?: boolean }>()
const emit = defineEmits<{ saved: [request: RequestDetail]; busy: [value: boolean]; reload: [] }>()
const action = ref<ReviewFields['action'] | null>(null)
const responsible = ref<string | null>(null)
const classification = ref<ReviewFields['classification']>(null)
const message = ref('')
const saving = ref(false)
const needsReload = ref(false)
const serverError = ref('')
const locked = computed(() => saving.value || needsReload.value || Boolean(props.disabled))
const form = ref<HTMLFormElement | null>(null)
const errorKeys = ['responsible_id', 'classification', 'message', 'row_version'] as const
const errors = reactive({ responsible_id: '', classification: '', message: '', row_version: '' })
const prefix = 'request-review-' + props.request.id
const classifications = [{ label: 'Melhoria', value: 'melhoria' }, { label: 'Projeto', value: 'projeto' }]
const actions: { value: ReviewFields['action']; label: string; icon: string; tone: 'success' | 'danger' | 'neutral' }[] = [
  { value: 'accept', label: 'Aceitar', icon: 'pi pi-check', tone: 'success' },
  { value: 'reject', label: 'Recusar', icon: 'pi pi-times', tone: 'danger' },
  { value: 'request_information', label: 'Solicitar mais informações', icon: 'pi pi-comment', tone: 'neutral' },
]
const selectedTone = computed(() => actions.find(option => option.value === action.value)?.tone ?? 'neutral')
const { data: responsibles, isPending, isError, refetch } = useQuery({
  queryKey: ['demands', 'management', 'responsibles'], queryFn: demandsApi.responsibles,
  enabled: computed(() => action.value === 'accept'), retry: false,
  refetchOnWindowFocus: false, refetchOnReconnect: false,
})
watch(saving, value => emit('busy', value), { flush: 'sync' })

async function choose(value: ReviewFields['action']) {
  if (locked.value) return
  action.value = value
  errorKeys.forEach(key => { errors[key] = '' })
  serverError.value = ''
  await nextTick()
  document.getElementById(prefix + (value === 'accept' ? '-responsible' : '-message'))?.focus()
}
async function focusError() {
  await nextTick()
  form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
}
async function submit() {
  if (locked.value || !action.value) return
  errorKeys.forEach(key => { errors[key] = '' })
  serverError.value = ''
  if (action.value === 'accept') {
    if (!responsible.value) errors.responsible_id = 'Selecione o responsável.'
    if (props.request.entry_kind === 'demanda' && !classification.value) errors.classification = 'Selecione Melhoria ou Projeto.'
  } else if (!message.value.trim()) {
    errors.message = action.value === 'reject' ? 'Informe o motivo da recusa.' : 'Descreva quais informações são necessárias.'
  }
  if (errorKeys.some(key => errors[key])) { await focusError(); return }
  saving.value = true
  let saved: RequestDetail | undefined
  try {
    saved = await demandsApi.review(props.request.id, {
      action: action.value, row_version: props.request.row_version,
      responsible_id: action.value === 'accept' ? responsible.value : null,
      classification: action.value === 'accept' && props.request.entry_kind === 'demanda' ? classification.value : null,
      message: action.value !== 'accept' ? message.value.trim() : null,
    })
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível registrar a decisão.'
    if (error instanceof ApiError) {
      Object.assign(errors, validationMessages(error.detail, errorKeys))
      needsReload.value = [0, 401, 403, 409].includes(error.status) || error.status >= 500
        || (error.status >= 200 && error.status < 300)
    } else {
      needsReload.value = true
    }
  } finally {
    saving.value = false
  }
  if (saved) emit('saved', saved)
  else await focusError()
}
</script>

<template>
  <section class="mt-6 border-t border-dj-border pt-5" :aria-labelledby="prefix + '-title'">
    <h4 :id="prefix + '-title'" tabindex="-1" class="text-sm font-semibold">Analisar solicitação</h4>
    <p class="mt-2 text-sm leading-6 text-dj-muted">Confira os dados antes de registrar sua decisão.</p>
    <div class="mt-4 flex flex-wrap gap-2" role="group" aria-label="Decisão sobre a solicitação">
      <Button v-for="option in actions" :key="option.value" type="button" :label="option.label" :icon="option.icon"
        class="dj-action-soft rounded-xl px-4 py-2.5" :class="'dj-tone-' + option.tone"
        :aria-pressed="action === option.value" :disabled="locked"
        :aria-controls="prefix + '-form'" @click="choose(option.value)" />
    </div>
    <form v-if="action" :id="prefix + '-form'" ref="form" class="mt-5 space-y-4" novalidate @submit.prevent="submit">
      <Message v-if="serverError" severity="error" role="alert">{{ serverError }}</Message>
      <Message v-if="errors.row_version" severity="error">{{ errors.row_version }}</Message>
      <template v-if="action === 'accept'">
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField :id="prefix + '-responsible'" label="Responsável *" :error="errors.responsible_id" v-slot="{ controlProps }">
            <Select v-model="responsible" :input-id="controlProps.id" :invalid="controlProps.invalid"
              :pt:label:aria-invalid="controlProps['aria-invalid']" :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true"
              :options="responsibles?.items ?? []" option-label="name" option-value="id" filter
              :loading="isPending" :disabled="locked || isPending || isError" placeholder="Selecione o responsável" class="w-full" />
          </FormField>
          <FormField v-if="request.entry_kind === 'demanda'" :id="prefix + '-classification'" label="Classificação *"
            :error="errors.classification" v-slot="{ controlProps }">
            <Select v-model="classification" :input-id="controlProps.id" :invalid="controlProps.invalid"
              :pt:label:aria-invalid="controlProps['aria-invalid']" :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true"
              :options="classifications" option-label="label" option-value="value" :disabled="locked"
              placeholder="Melhoria ou Projeto" class="w-full" />
          </FormField>
        </div>
        <div v-if="isError" role="alert" class="text-sm text-dj-danger">
          Não foi possível carregar os responsáveis.
          <SecondaryButton type="button" label="Tentar novamente" :disabled="locked" @click="refetch()" />
        </div>
        <p v-else-if="!isPending && !responsibles?.items.length" class="text-sm text-dj-muted">Nenhum responsável ativo disponível na equipe.</p>
        <p v-if="request.entry_kind === 'erro'" class="text-sm text-dj-muted">Este registro continuará identificado como relato de erro.</p>
      </template>
      <FormField v-else :id="prefix + '-message'" :label="action === 'reject' ? 'Motivo da recusa *' : 'Informações necessárias *'"
        :error="errors.message" v-slot="{ controlProps }">
        <Textarea v-model="message" v-bind="controlProps" required :rows="4" :maxlength="4000" :disabled="locked" class="w-full"
          :placeholder="action === 'reject' ? 'Explique por que esta solicitação está sendo recusada.' : 'Descreva o que o solicitante precisa complementar.'" />
      </FormField>
      <p v-if="action !== 'accept'" class="text-xs leading-5 text-dj-muted">A mensagem ficará disponível para o solicitante no histórico da solicitação.</p>
      <p v-if="needsReload" role="status" class="text-sm leading-6 text-dj-muted">Recarregue e confira o estado e o histórico antes de registrar outra decisão.</p>
      <div class="flex flex-wrap gap-3">
        <Button v-if="needsReload" type="button" label="Recarregar detalhes" icon="pi pi-refresh" :disabled="disabled" @click="emit('reload')" />
        <Button v-else type="submit" :label="action === 'accept' ? 'Confirmar aceite' : action === 'reject' ? 'Confirmar recusa' : 'Confirmar pedido de informações'"
          class="dj-action-soft" :class="'dj-tone-' + selectedTone" :loading="saving" :disabled="locked || (action === 'accept' && (isPending || isError || !responsibles?.items.length))" />
        <SecondaryButton type="button" label="Cancelar" outlined :disabled="locked" @click="action = null" />
      </div>
    </form>
  </section>
</template>
