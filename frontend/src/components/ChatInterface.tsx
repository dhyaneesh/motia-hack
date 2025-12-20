'use client';
import { useState, useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Spinner,
  useToast,
  IconButton,
  InputGroup,
  InputRightElement,
  Heading
} from '@chakra-ui/react';
import { AttachmentIcon } from '@chakra-ui/icons';
import { useGraph } from '@/contexts/GraphContext';
import { useMode, Mode } from '@/contexts/ModeContext';
import { api } from '@/services/api';
import { ChatMessage } from '@/types';

export function ChatInterface() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const { setGraph } = useGraph();
  const { currentMode, setMode } = useMode();
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
    if ((!question.trim() && !imageBase64) || isLoading) return;
    
    const userMessage: ChatMessage = { 
      role: 'user', 
      content: question || (imageBase64 ? '[Image uploaded]' : '') 
    };
    setMessages(prev => [...prev, userMessage]);
    const currentQuestion = question;
    setQuestion('');
    setIsLoading(true);
    
    try {
      let response;
      
      // Route to mode-specific endpoints
      if (currentMode === 'shopping') {
        response = await api.shopping(currentQuestion || 'products');
        // Transform shopping response to match expected format
        response = {
          answer: `Found ${response.products.length} products`,
          graph: response.graph
        };
      } else if (currentMode === 'study') {
        response = await api.study(currentQuestion);
      } else {
        // Default mode
        response = await api.chat(currentQuestion, currentMode, imageBase64 || undefined);
      }
      
      const assistantMessage: ChatMessage = { 
        role: 'assistant', 
        content: response.answer 
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Update graph
      if (response.graph) {
        setGraph(response.graph);
      }
      
      // Clear image after use
      if (imageBase64) {
        setImageBase64(null);
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to process request',
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
      {/* App Header */}
      <Box w="100%" borderBottom="1px" borderColor="gray.200" bg="white" p={3}>
        <HStack spacing={2} align="center">
          <Heading size="md" color="blue.600" fontWeight="bold">
            Dive
          </Heading>
          <Text fontSize="xs" color="gray.600" fontStyle="italic">
            Searching Redefined
          </Text>
        </HStack>
      </Box>
      
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
      <Box w="100%" p={4} borderTop="1px" borderColor="gray.200" bg="white">
        {/* Mode Switcher */}
        <HStack spacing={2} mb={3} justify="center">
          {(['default', 'shopping', 'study'] as Mode[]).map((mode) => (
            <Button
              key={mode}
              size="xs"
              colorScheme={currentMode === mode ? (mode === 'shopping' ? 'blue' : mode === 'study' ? 'green' : 'gray') : 'gray'}
              variant={currentMode === mode ? 'solid' : 'outline'}
              onClick={() => setMode(mode)}
            >
              {mode === 'default' ? 'Default' : mode === 'shopping' ? 'Shopping' : 'Study'}
            </Button>
          ))}
        </HStack>
        
        <form onSubmit={handleSubmit}>
          <VStack spacing={2}>
            <InputGroup>
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={currentMode === 'shopping' ? 'Search for products...' : currentMode === 'study' ? 'Ask a question to learn...' : 'Ask a question...'}
                isDisabled={isLoading}
                pr="40px"
              />
              <InputRightElement width="40px">
                <input
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="image-upload"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (!file.type.startsWith('image/')) {
                      toast({ title: 'Error', description: 'Please select an image file', status: 'error', duration: 3000 });
                      return;
                    }
                    if (file.size > 5 * 1024 * 1024) {
                      toast({ title: 'Error', description: 'Image size must be less than 5MB', status: 'error', duration: 3000 });
                      return;
                    }
                    const reader = new FileReader();
                    reader.onloadend = () => {
                      const result = reader.result as string;
                      const base64 = result.split(',')[1];
                      setImageBase64(base64);
                    };
                    reader.readAsDataURL(file);
                  }}
                />
                <IconButton
                  aria-label="Upload image"
                  icon={<AttachmentIcon />}
                  size="sm"
                  variant="ghost"
                  onClick={() => document.getElementById('image-upload')?.click()}
                  isDisabled={isLoading}
                />
              </InputRightElement>
            </InputGroup>
            {imageBase64 && (
              <HStack w="100%" justify="space-between" p={2} bg="gray.50" borderRadius="md">
                <Text fontSize="xs" color="gray.600">Image attached</Text>
                <Button size="xs" variant="ghost" onClick={() => setImageBase64(null)}>Remove</Button>
              </HStack>
            )}
            <Button
              type="submit"
              colorScheme="blue"
              w="100%"
              isDisabled={isLoading || (!question.trim() && !imageBase64)}
            >
              {isLoading ? 'Processing...' : 'Send'}
            </Button>
          </VStack>
        </form>
      </Box>
    </VStack>
  );
}

