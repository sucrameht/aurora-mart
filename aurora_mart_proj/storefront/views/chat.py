from django.shortcuts import render, redirect, get_object_or_404
from ..models import *
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin

class StartChatView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        sku_code = self.kwargs.get('sku_code')
        product = get_object_or_404(Product, sku_code=sku_code)
        
        thread, created = ChatThread.objects.get_or_create(
            product=product,
            customer=request.user
        )
        
        return redirect('chat_thread', thread_id=thread.pk)

class ChatListView(LoginRequiredMixin, ListView):
    model = ChatThread
    template_name = 'chat_list.html'
    context_object_name = 'threads'

    def get_queryset(self):
        return ChatThread.objects.filter(customer=self.request.user).order_by('-updated_at')

class ChatThreadView(LoginRequiredMixin, View):
    template_name = 'chat_thread.html'

    def get(self, request, *args, **kwargs):
        thread_id = self.kwargs.get('thread_id')
        thread = get_object_or_404(ChatThread, pk=thread_id, customer=request.user)
        # messages = thread.messages.all()
        context = {
            'thread': thread,
            # 'messages': messages
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        thread_id = self.kwargs.get('thread_id')
        thread = get_object_or_404(ChatThread, pk=thread_id, customer=request.user)
        
        message = request.POST.get('message')
        if message:
            ChatMessage.objects.create(
                thread=thread,
                sender=request.user,
                message=message
            )
            thread.save()
        
        return redirect('chat_thread', thread_id=thread.pk)