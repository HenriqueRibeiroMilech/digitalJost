<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from '@/volt/Button.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import FormField from '@/shared/components/FormField.vue'
import { demandsApi } from '../api'
import { displayDate, fileAccept } from '../presentation'
import type { InformationRequest } from '../types'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
const props = defineProps<{ demandId: number; version: string; items: InformationRequest[]; canReply?: boolean }>()
const emit = defineEmits<{ changed: []; busy: [value: boolean] }>()
const reply = ref(''); const files = ref<File[]>([]); const busy = ref(false); const error = ref(''); const warning = ref('')
const pending = computed(() => props.items.find(item => !item.closed_at))
watch(busy, value => emit('busy', value), { flush: 'sync' })
async function send() {
  if (busy.value || !pending.value) return
  if (!reply.value.trim()) { error.value = 'Informe a resposta ou os detalhes da reunião agendada.'; return }
  error.value = ''; busy.value = true
  try {
    const result = await demandsApi.reply(props.demandId, { row_version: props.version, information_id: pending.value.id, reply: reply.value.trim() }, files.value)
    warning.value = result.notification_warning ?? ''; reply.value = ''; files.value = []
    emit('changed')
  } catch (err) {
    if (err instanceof ApiError) {
      const messages = validationMessages(err.detail, ['reply', 'files'])
      error.value = messages.reply || messages.files || err.message
    } else error.value = err instanceof Error ? err.message : 'Não foi possível enviar a resposta.'
  }
  finally { busy.value = false }
}
</script>
<template>
  <section v-if="items.length" class="space-y-4" aria-label="Pedidos de informações e reuniões">
    <article v-for="item in items" :key="item.id" class="rounded-xl border border-dj-border bg-dj-canvas p-4">
      <h4 class="text-sm font-semibold">{{ item.kind === 'reuniao' ? 'Solicitação de reunião' : 'Pedido de informações' }} · {{ item.closed_at ? 'Encerrado' : 'Aguardando resposta' }}</h4>
      <p class="mt-1 text-xs text-dj-muted">{{ item.requested_by_name ?? 'Equipe responsável' }} · {{ displayDate(item.requested_at) }}</p>
      <p class="mt-3 whitespace-pre-wrap break-words text-sm leading-6">{{ item.question }}</p>
      <div v-if="item.reply" class="mt-3 rounded-lg bg-dj-surface p-3">
        <p class="text-xs font-medium">Resposta de {{ item.replied_by_name ?? 'Solicitante' }}</p>
        <p class="mt-2 whitespace-pre-wrap break-words text-sm">{{ item.reply }}</p>
      </div>
    </article>
    <form v-if="canReply && pending" :aria-busy="busy" @submit.prevent="send" class="space-y-4 rounded-xl border border-dj-border p-4">
      <FormField :id="'information-reply-' + demandId" v-slot="{ controlProps }" label="Sua resposta *" :error="error">
        <Textarea v-bind="controlProps" v-model="reply" :maxlength="4000" :rows="4" :disabled="busy" class="w-full"
          placeholder="Complemente as informações ou informe os detalhes da reunião agendada." />
      </FormField>
      <label class="block text-sm">Documentos adicionais (opcional)
        <input type="file" multiple :accept="fileAccept" :disabled="busy" class="mt-2 block w-full text-sm"
          @change="files = Array.from(($event.target as HTMLInputElement).files ?? [])" />
      </label>
      <p class="text-xs text-dj-muted">Até 10 arquivos por envio, 10 MB por arquivo e 40 MB no total.</p>
      <Button type="submit" label="Enviar resposta" :loading="busy" :disabled="busy" />
    </form>
    <Message v-if="warning" severity="warn">{{ warning }}</Message>
  </section>
</template>
