'use client';
import { useState, useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  Input,
  Button,
  Text,
  Spinner,
  useToast
} from '@chakra-ui/react';
import { useGraph } from '@/contexts/GraphContext';
import { api } from '@/services/api';
import { ChatMessage } from '@/types';

export function ChatInterface() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { setGraph } = useGraph();
  const toast = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;
    
    const userMessage: ChatMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setQuestion('');
    setIsLoading(true);
    
    try {
      const response = await api.chat(question);
      
      const assistantMessage: ChatMessage = { 
        role: 'assistant', 
        content: response.answer 
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Update graph
      setGraph(response.graph);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to process question',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <VStack h="100vh" spacing={0}>
      {/* Messages */}
      <Box flex={1} overflowY="auto" w="100%" p={4}>
        <VStack align="stretch" spacing={4}>
          {messages.map((msg, idx) => (
            <Box
              key={idx}
              alignSelf={msg.role === 'user' ? 'flex-end' : 'flex-start'}
              maxW="80%"
              p={3}
              borderRadius="lg"
              bg={msg.role === 'user' ? 'blue.500' : 'gray.100'}
              color={msg.role === 'user' ? 'white' : 'black'}
            >
              <Text fontSize="sm" whiteSpace="pre-wrap">
                {msg.content}
              </Text>
            </Box>
          ))}
          {isLoading && (
            <Box alignSelf="flex-start" p={3}>
              <Spinner size="sm" />
            </Box>
          )}
          <div ref={messagesEndRef} />
        </VStack>
      </Box>
      
      {/* Input */}
      <Box w="100%" p={4} borderTop="1px" borderColor="gray.200">
        <form onSubmit={handleSubmit}>
          <VStack spacing={2}>
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question..."
              isDisabled={isLoading}
            />
            <Button
              type="submit"
              colorScheme="blue"
              w="100%"
              isDisabled={isLoading || !question.trim()}
            >
              {isLoading ? 'Processing...' : 'Send'}
            </Button>
          </VStack>
        </form>
      </Box>
    </VStack>
  );
}

