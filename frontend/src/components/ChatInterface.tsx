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
import ReactMarkdown from 'react-markdown';
import { useGraph } from '@/contexts/GraphContext';
import { useMode, Mode } from '@/contexts/ModeContext';
import { api } from '@/services/api';
import { ChatMessage } from '@/types';

export function ChatInterface() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const { graph, setGraph, addToGraph } = useGraph();
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
    const currentQuestion = question;
    
    // Extract previous query for context-aware graph merging (before adding current message)
    const previousUserMessages = messages.filter(m => m.role === 'user');
    const previousQuery = previousUserMessages.length > 0 ? previousUserMessages.slice(-1)[0]?.content || null : null;
    
    setMessages(prev => [...prev, userMessage]);
    setQuestion('');
    setIsLoading(true);
    
    try {
      let initialResponse;
      let requestId: string;
      
      // Route to mode-specific endpoints
      if (currentMode === 'shopping') {
        initialResponse = await api.shopping(currentQuestion || 'products');
        requestId = initialResponse.requestId;
        // Show immediate response
        const assistantMessage: ChatMessage = { 
          role: 'assistant', 
          content: 'Searching for products...' 
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Poll for completion
        try {
          const status = await api.pollChatStatus(requestId, (status) => {
            // Update message with progress
            if (status.status === 'processing') {
              setMessages(prev => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === 'assistant') {
                  lastMsg.content = 'Processing products...';
                }
                return updated;
              });
            }
          });
          
          if (status.status === 'completed' && status.graph) {
            setGraph(status.graph);
            setMessages(prev => {
              const updated = [...prev];
              const lastMsg = updated[updated.length - 1];
              if (lastMsg && lastMsg.role === 'assistant') {
                lastMsg.content = `Found products. Graph ready!`;
              }
              return updated;
            });
          }
        } catch (pollError: any) {
          console.error('Polling error:', pollError);
        }
      } else if (currentMode === 'study') {
        initialResponse = await api.study(currentQuestion);
        requestId = initialResponse.requestId;
        
        // Show answer immediately
        const assistantMessage: ChatMessage = { 
          role: 'assistant', 
          content: initialResponse.answer 
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Poll for graph completion
        try {
          const status = await api.pollChatStatus(requestId, (status) => {
            // Optional: show progress updates
          });
          
          if (status.status === 'completed' && status.graph) {
            setGraph(status.graph);
          }
        } catch (pollError: any) {
          console.error('Polling error:', pollError);
        }
      } else {
        // Default mode - pass previous query for continuous graph building
        initialResponse = await api.chat(currentQuestion, currentMode, imageBase64 || undefined, previousQuery);
        requestId = initialResponse.requestId;
        
        // Show answer immediately
        const assistantMessage: ChatMessage = { 
          role: 'assistant', 
          content: initialResponse.answer 
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Poll for graph completion
        try {
          const status = await api.pollChatStatus(requestId, (status) => {
            // Optional: show progress updates in UI
            if (status.status === 'processing') {
              setMessages(prev => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === 'assistant') {
                  lastMsg.content = `${initialResponse.answer}\n\n[Building knowledge graph...]`;
                }
                return updated;
              });
            }
          });
          
          if (status.status === 'completed' && status.graph) {
            // Backend handles merging, so we just set the complete graph
            setGraph(status.graph);
            // Update message to remove processing indicator
            setMessages(prev => {
              const updated = [...prev];
              const lastMsg = updated[updated.length - 1];
              if (lastMsg && lastMsg.role === 'assistant') {
                lastMsg.content = initialResponse.answer;
              }
              return updated;
            });
          } else if (status.status === 'failed') {
            toast({
              title: 'Error',
              description: status.error || 'Failed to build graph',
              status: 'error',
              duration: 5000,
              isClosable: true
            });
          }
        } catch (pollError: any) {
          console.error('Polling error:', pollError);
          toast({
            title: 'Warning',
            description: 'Graph building may still be in progress',
            status: 'warning',
            duration: 3000,
            isClosable: true
          });
        }
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
              {msg.role === 'assistant' ? (
                <Box fontSize="sm" sx={{ 
                  '& p:last-child': { mb: 0 },
                  '& ul, & ol': { mb: 2 },
                  '& li': { mb: 1 }
                }}>
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <Text mb={2} lineHeight="1.6">{children}</Text>,
                      h1: ({ children }) => <Heading as="h1" size="md" mb={2} mt={4}>{children}</Heading>,
                      h2: ({ children }) => <Heading as="h2" size="sm" mb={2} mt={3}>{children}</Heading>,
                      h3: ({ children }) => <Heading as="h3" size="xs" mb={1} mt={2}>{children}</Heading>,
                      ul: ({ children }) => <Box as="ul" pl={4} mb={2} style={{ listStyleType: 'disc' }}>{children}</Box>,
                      ol: ({ children }) => <Box as="ol" pl={4} mb={2} style={{ listStyleType: 'decimal' }}>{children}</Box>,
                      li: ({ children }) => <Box as="li" mb={1} lineHeight="1.6">{children}</Box>,
                      code: ({ children, className, ...props }) => {
                        // Inline code doesn't have className, code blocks do
                        const isInline = !className;
                        return (
                          <Box
                            as="code"
                            bg={isInline ? 'gray.200' : 'transparent'}
                            color={isInline ? 'gray.800' : 'gray.100'}
                            px={isInline ? 1.5 : 0}
                            py={isInline ? 0.5 : 0}
                            borderRadius="md"
                            fontSize={isInline ? '0.85em' : 'xs'}
                            fontFamily="mono"
                            display={isInline ? 'inline' : 'block'}
                            {...props}
                          >
                            {children}
                          </Box>
                        );
                      },
                      pre: ({ children }) => (
                        <Box
                          as="pre"
                          bg="gray.800"
                          color="gray.100"
                          p={3}
                          borderRadius="md"
                          fontSize="xs"
                          fontFamily="mono"
                          overflowX="auto"
                          mb={2}
                          mt={2}
                        >
                          {children}
                        </Box>
                      ),
                      blockquote: ({ children }) => (
                        <Box
                          as="blockquote"
                          borderLeft="4px solid"
                          borderColor="gray.400"
                          pl={3}
                          my={2}
                          fontStyle="italic"
                          color="gray.700"
                        >
                          {children}
                        </Box>
                      ),
                      a: ({ href, children }) => (
                        <Text
                          as="a"
                          href={href}
                          color="blue.600"
                          textDecoration="underline"
                          _hover={{ color: 'blue.700' }}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {children}
                        </Text>
                      ),
                      strong: ({ children }) => <Text as="strong" fontWeight="bold">{children}</Text>,
                      em: ({ children }) => <Text as="em" fontStyle="italic">{children}</Text>,
                      hr: () => <Box as="hr" borderColor="gray.300" my={3} />,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </Box>
              ) : (
                <Text fontSize="sm" whiteSpace="pre-wrap">
                  {msg.content}
                </Text>
              )}
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

