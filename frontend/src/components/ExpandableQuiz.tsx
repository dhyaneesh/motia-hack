'use client';
import {
  Box,
  Button,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  VStack,
  HStack,
  Text,
  Heading,
  Radio,
  RadioGroup,
  Input,
  Badge,
  useToast
} from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
import { api } from '@/services/api';

interface QuizQuestion {
  type: 'multiple_choice' | 'true_false' | 'short_answer';
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  concept_id: string;
}

export function ExpandableQuiz() {
  const { graph } = useGraph();
  const { currentMode } = useMode();
  const [isOpen, setIsOpen] = useState(false);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);
  const [score, setScore] = useState(0);
  const toast = useToast();
  
  // Only show in study mode when graph has nodes
  if (currentMode !== 'study' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  useEffect(() => {
    if (isOpen && questions.length === 0) {
      generateQuiz();
    }
  }, [isOpen]);
  
  const generateQuiz = async () => {
    try {
      // Extract concepts from graph
      const concepts = graph.nodes.map(node => ({
        id: node.id,
        name: node.data?.name || 'Unknown',
        description: node.data?.description || ''
      }));
      
      if (concepts.length === 0) {
        toast({
          title: 'No concepts available',
          description: 'Complete a study query first to generate a quiz',
          status: 'warning',
          duration: 3000
        });
        return;
      }
      
      // Generate mock questions (would call API in production)
      const mockQuestions: QuizQuestion[] = concepts.slice(0, 5).map((concept, idx) => ({
        type: 'multiple_choice',
        question: `What is ${concept.name}?`,
        options: [
          concept.description.substring(0, 50) || 'Option 1',
          'Option 2',
          'Option 3',
          'Option 4'
        ],
        correct_answer: concept.description.substring(0, 50) || 'Option 1',
        explanation: `See ${concept.name} for details.`,
        concept_id: concept.id
      }));
      
      setQuestions(mockQuestions);
      setCurrentQuestion(0);
      setAnswers({});
      setShowResults(false);
      setScore(0);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to generate quiz',
        status: 'error',
        duration: 5000
      });
    }
  };
  
  const handleAnswer = (answer: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion]: answer }));
  };
  
  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      calculateScore();
      setShowResults(true);
    }
  };
  
  const calculateScore = () => {
    let correct = 0;
    questions.forEach((q, idx) => {
      if (answers[idx] === q.correct_answer) {
        correct++;
      }
    });
    setScore(correct);
  };
  
  const question = questions[currentQuestion];
  const userAnswer = answers[currentQuestion];
  
  return (
    <Box position="absolute" top={4} left={120} zIndex={10}>
      <Popover isOpen={isOpen} onOpen={() => setIsOpen(true)} onClose={() => setIsOpen(false)} placement="bottom-start">
        <PopoverTrigger>
          <Button size="sm" colorScheme="green" variant="outline">
            Quiz
          </Button>
        </PopoverTrigger>
        <PopoverContent w="400px" maxH="600px" overflowY="auto">
          <PopoverBody>
            {questions.length === 0 ? (
              <VStack spacing={4}>
                <Text fontSize="sm" color="gray.500">
                  Generate quiz questions from your study concepts
                </Text>
                <Button size="sm" colorScheme="blue" onClick={generateQuiz}>
                  Generate Quiz
                </Button>
              </VStack>
            ) : !showResults ? (
              <VStack align="stretch" spacing={4}>
                <HStack justify="space-between">
                  <Heading size="sm">Quiz</Heading>
                  <Text fontSize="xs" color="gray.500">
                    Question {currentQuestion + 1} of {questions.length}
                  </Text>
                </HStack>
                
                <Text fontSize="md" fontWeight="medium">
                  {question.question}
                </Text>
                
                {question.type === 'multiple_choice' && question.options && (
                  <RadioGroup value={userAnswer || ''} onChange={handleAnswer}>
                    <VStack align="stretch" spacing={2}>
                      {question.options.map((option, idx) => (
                        <Radio key={idx} value={option}>
                          {option}
                        </Radio>
                      ))}
                    </VStack>
                  </RadioGroup>
                )}
                
                {question.type === 'true_false' && (
                  <RadioGroup value={userAnswer || ''} onChange={handleAnswer}>
                    <VStack align="stretch" spacing={2}>
                      <Radio value="true">True</Radio>
                      <Radio value="false">False</Radio>
                    </VStack>
                  </RadioGroup>
                )}
                
                {question.type === 'short_answer' && (
                  <Input
                    value={userAnswer || ''}
                    onChange={(e) => handleAnswer(e.target.value)}
                    placeholder="Your answer..."
                  />
                )}
                
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentQuestion(prev => Math.max(0, prev - 1))}
                    isDisabled={currentQuestion === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="blue"
                    onClick={handleNext}
                    isDisabled={!userAnswer}
                    flex={1}
                  >
                    {currentQuestion === questions.length - 1 ? 'Finish' : 'Next'}
                  </Button>
                </HStack>
              </VStack>
            ) : (
              <VStack align="stretch" spacing={4}>
                <HStack justify="space-between">
                  <Heading size="sm">Quiz Complete!</Heading>
                  <Badge colorScheme={score >= questions.length / 2 ? 'green' : 'red'}>
                    {score}/{questions.length}
                  </Badge>
                </HStack>
                <Text fontSize="md">
                  You scored {score} out of {questions.length}
                </Text>
                <Button size="sm" colorScheme="blue" onClick={() => {
                  setShowResults(false);
                  setCurrentQuestion(0);
                  setAnswers({});
                }}>
                  Retake Quiz
                </Button>
              </VStack>
            )}
          </PopoverBody>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
